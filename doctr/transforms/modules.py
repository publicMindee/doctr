# Copyright (C) 2021, Mindee.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

import random
import tensorflow as tf
from typing import List, Any, Tuple, Callable

from doctr.utils.repr import NestedObject
from . import functional as F


__all__ = ['Compose', 'Resize', 'Normalize', 'LambdaTransformation', 'ToGray', 'ColorInversion',
           'RandomBrightness', 'RandomContrast', 'RandomSaturation', 'RandomHue', 'RandomGamma', 'RandomJpegQuality',
           'OneOf', 'RandomApply']


class Compose(NestedObject):
    """Implements a wrapper that will apply transformations sequentially

    Example::
        >>> from doctr.transforms import Compose, Resize
        >>> import tensorflow as tf
        >>> transfos = Compose([Resize((32, 32))])
        >>> out = transfos(tf.random.uniform(shape=[64, 64, 3], minval=0, maxval=1))

    Args:
        transforms: list of transformation modules
    """

    _children_names: List[str] = ['transforms']

    def __init__(self, transforms: List[NestedObject]) -> None:
        self.transforms = transforms

    def __call__(self, x: Any) -> Any:
        for t in self.transforms:
            x = t(x)

        return x


class Resize(NestedObject):
    """Resizes a tensor to a target size

    Example::
        >>> from doctr.transforms import Resize
        >>> import tensorflow as tf
        >>> transfo = Resize((32, 32))
        >>> out = transfo(tf.random.uniform(shape=[64, 64, 3], minval=0, maxval=1))

    Args:
        output_size: expected output size
        method: interpolation method
        preserve_aspect_ratio: if `True`, preserve aspect ratio and pad the rest with zeros
    """
    def __init__(
        self,
        output_size: Tuple[int, int],
        method: str = 'bilinear',
        preserve_aspect_ratio: bool = False,
    ) -> None:
        self.output_size = output_size
        self.method = method
        self.preserve_aspect_ratio = preserve_aspect_ratio

    def extra_repr(self) -> str:
        return f"output_size={self.output_size}, method='{self.method}'"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        img = tf.image.resize(img, self.output_size, self.method, self.preserve_aspect_ratio)
        if self.preserve_aspect_ratio:
            img = tf.image.pad_to_bounding_box(img, 0, 0, *self.output_size)
        return img


class Normalize(NestedObject):
    """Normalize a tensor to a Gaussian distribution for each channel

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        mean: average value per channel
        std: standard deviation per channel
    """
    def __init__(self, mean: Tuple[float, float, float], std: Tuple[float, float, float]) -> None:
        self.mean = tf.constant(mean, dtype=tf.float32)
        self.std = tf.constant(std, dtype=tf.float32)

    def extra_repr(self) -> str:
        return f"mean={self.mean.numpy().tolist()}, std={self.std.numpy().tolist()}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        img -= self.mean
        img /= self.std
        return img


class LambdaTransformation(NestedObject):
    """Normalize a tensor to a Gaussian distribution for each channel

    Example::
        >>> from doctr.transforms import LambdaTransformation
        >>> import tensorflow as tf
        >>> transfo = LambdaTransformation(lambda x: x/ 255.)
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        fn: the function to be applied to the input tensor
    """
    def __init__(self, fn: Callable[[tf.Tensor], tf.Tensor]) -> None:
        self.fn = fn

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return self.fn(img)


class ToGray(NestedObject):
    """Convert a RGB tensor (batch of images or image) to a 3-channels grayscale tensor

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = ToGray()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))
    """
    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.rgb_to_grayscale(img)


class ColorInversion(NestedObject):
    """Applies the following tranformation to a tensor (image or batch of images):
    convert to grayscale, colorize (shift 0-values randomly), and then invert colors

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = ColorInversion(min_val=0.6)
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        min_val: range [min_val, 1] to colorize RGB pixels
    """
    def __init__(self, min_val: float = 0.6) -> None:
        self.min_val = min_val

    def extra_repr(self) -> str:
        return f"min_val={self.min_val}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return F.invert_colors(img, self.min_val)


class RandomBrightness(NestedObject):
    """Randomly adjust brightness of a tensor (batch of images or image) by adding a delta
    to all pixels

    Example:
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Brightness()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        max_delta: offset to add to each pixel is randomly picked in [-max_delta, max_delta]
        p: probability to apply transformation
    """
    def __init__(self, max_delta: float = 0.3) -> None:
        self.max_delta = max_delta

    def extra_repr(self) -> str:
        return f"max_delta={self.max_delta}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.random_brightness(img, max_delta=self.max_delta)


class RandomContrast(NestedObject):
    """Randomly adjust contrast of a tensor (batch of images or image) by adjusting
    each pixel: (img - mean) * contrast_factor + mean.

    Example:
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Contrast()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        delta: multiplicative factor is picked in [1-delta, 1+delta] (reduce contrast if factor<1)
    """
    def __init__(self, delta: float = .3) -> None:
        self.delta = delta

    def extra_repr(self) -> str:
        return f"delta={self.delta}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.random_contrast(img, lower=1 - self.delta, upper=1 + self.delta)


class RandomSaturation(NestedObject):
    """Randomly adjust saturation of a tensor (batch of images or image) by converting to HSV and
    increasing saturation by a factor.

    Example:
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Saturation()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        delta: multiplicative factor is picked in [1-delta, 1+delta] (reduce saturation if factor<1)
    """
    def __init__(self, delta: float = .5) -> None:
        self.delta = delta

    def extra_repr(self) -> str:
        return f"delta={self.delta}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.random_saturation(img, lower=1 - self.delta, upper=1 + self.delta)


class RandomHue(NestedObject):
    """Randomly adjust hue of a tensor (batch of images or image) by converting to HSV and adding a delta

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Hue()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        max_delta: offset to add to each pixel is randomly picked in [-max_delta, max_delta]
    """
    def __init__(self, max_delta: float = 0.3) -> None:
        self.max_delta = max_delta

    def extra_repr(self) -> str:
        return f"max_delta={self.max_delta}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.random_hue(img, max_delta=self.max_delta)


class RandomGamma(NestedObject):
    """randomly performs gamma correction for a tensor (batch of images or image)

    Example:
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = Gamma()
        >>> out = transfo(tf.random.uniform(shape=[8, 64, 64, 3], minval=0, maxval=1))

    Args:
        min_gamma: non-negative real number, lower bound for gamma param
        max_gamma: non-negative real number, upper bound for gamma
        min_gain: lower bound for constant multiplier
        max_gain: upper bound for constant multiplier
    """
    def __init__(
        self,
        min_gamma: float = 0.5,
        max_gamma: float = 1.5,
        min_gain: float = 0.8,
        max_gain: float = 1.2,
    ) -> None:
        self.min_gamma = min_gamma
        self.max_gamma = max_gamma
        self.min_gain = min_gain
        self.max_gain = max_gain

    def extra_repr(self) -> str:
        return f"""gamma_range=({self.min_gamma}, {self.max_gamma}),
                 gain_range=({self.min_gain}, {self.max_gain})"""

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        gamma = random.uniform(self.min_gamma, self.max_gamma)
        gain = random.uniform(self.min_gain, self.max_gain)
        return tf.image.adjust_gamma(img, gamma=gamma, gain=gain)


class RandomJpegQuality(NestedObject):
    """Randomly adjust jpeg quality of a 3 dimensional RGB image

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = JpegQuality()
        >>> out = transfo(tf.random.uniform(shape=[64, 64, 3], minval=0, maxval=1))

    Args:
        min_quality: int between [0, 100], quality will be picked in [min_quality, 100]
    """
    def __init__(self, min_quality: int = 60) -> None:
        self.min_quality = min_quality

    def extra_repr(self) -> str:
        return f"min_quality={self.min_quality}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        return tf.image.random_jpeg_quality(
            img, min_jpeg_quality=self.min_quality, max_jpeg_quality=100
        )


class OneOf(NestedObject):
    """Randomly apply one of the input transformations

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = OneOf([JpegQuality(), Gamma()])
        >>> out = transfo(tf.random.uniform(shape=[64, 64, 3], minval=0, maxval=1))

    Args:
        transforms: list of transformations, one only will be picked
    """

    _children_names: List[str] = ['transforms']

    def __init__(self, transforms: List[NestedObject]) -> None:
        self.transforms = transforms

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        # Pick transformation
        transfo = self.transforms[int(random.random() * len(self.transforms))]
        # Apply
        return transfo(img)


class RandomApply(NestedObject):
    """Apply with a probability p the input transformation

    Example::
        >>> from doctr.transforms import Normalize
        >>> import tensorflow as tf
        >>> transfo = RandomApply(Gamma(), p=.5)
        >>> out = transfo(tf.random.uniform(shape=[64, 64, 3], minval=0, maxval=1))

    Args:
        transform: transformation to apply
        p: probability to apply
    """
    def __init__(self, transform: NestedObject, p: float = .5) -> None:
        self.transform = transform
        self.p = p

    def extra_repr(self) -> str:
        return f"transform={self.transform}, p={self.p}"

    def __call__(self, img: tf.Tensor) -> tf.Tensor:
        if random.random() < self.p:
            return self.transform(img)
        return img
