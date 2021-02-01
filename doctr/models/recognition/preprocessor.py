# Copyright (C) 2021, Mindee.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

import os
import math
import json
import numpy as np
import tensorflow as tf
from typing import Union, List, Tuple, Optional, Any, Dict

from ..preprocessor import PreProcessor

__all__ = ['RecognitionPreProcessor']


class RecognitionPreProcessor(PreProcessor):
    """Implements a recognition preprocessor

    Example::
        >>> from doctr.documents import read_pdf
        >>> from doctr.models import RecoPreprocessor
        >>> processor = RecoPreprocessor(output_size=(600, 600), batch_size=8)
        >>> processed_doc = processor([read_pdf("path/to/your/doc.pdf")])

    Args:
        output_size: expected size of each page in format (H, W)
        batch_size: the size of page batches
        mean: mean value of the training distribution by channel
        std: standard deviation of the training distribution by channel
    """

    def __init__(
        self,
        output_size: Tuple[int, int],
        batch_size: int,
        mean: Tuple[float, float, float] = (.5, .5, .5),
        std: Tuple[float, float, float] = (1., 1., 1.),
        interpolation: str = 'bilinear',
    ) -> None:

        super().__init__(output_size, batch_size, mean, std, interpolation)

    def resize_fixed_h(
        self,
        x: tf.Tensor,
    ) -> tf.Tensor:
        """Resize images using tensorflow backend.
        The images is resized to (output_height, width) where width is computed as follow :
            - If (preserving aspect-ratio width) output_height/image_height * image_width < output__width :
                resize to (output_height, output_height/image_height * image_width)
            - Else :
                resize to (output_height, output_width)

        Args:
            x: image as a tf.Tensor

        Returns:
            the processed image after being resized
        """
        image_shape = tf.shape(x)
        image_height = tf.cast(image_shape[0], dtype=tf.float32)
        image_width = tf.cast(image_shape[1], dtype=tf.float32)

        scale = self.output_size[0] / image_height
        max_width = tf.cast(self.output_size[1], tf.int32)
        new_width = tf.minimum(tf.cast(scale * image_width, dtype=tf.int32), max_width)

        return tf.image.resize(x, [self.output_size[0], new_width], method=self.interpolation)

    def pad(
        self,
        x: tf.Tensor,
    ) -> tf.Tensor:
        """Pads the image source with 0 to the right to match target_width and to the bottom to match target_height
        Be careful image height must not be greater than target_height
        Be careful image width must not be greater than target_width

        Args:
            x: an image as a tf.Tensor
            target_height: the output image height
            target_width: the output image width

        Returns:
            tensor with shape (target_height, target_width)
        """
        return tf.image.pad_to_bounding_box(x, 0, 0, self.output_size[0], self.output_size[1])

    def __call__(
        self,
        x: List[np.ndarray]
    ) -> List[tf.Tensor]:
        """Prepare document data for model forwarding

        Args:
            x: list of images (np.array)
        Returns:
            list of page batches
        """
        # convert images to tf
        tensors = [tf.cast(sample, dtype=tf.float32) for sample in x]
        # Resize the inputs
        images = [self.resize_fixed_h(sample) for sample in tensors]
        # pad inputs
        padded_images = [self.pad(sample) for sample in images]
        # Batch them
        processed_batches = self.batch_inputs(padded_images)
        # Normalize
        processed_batches = [self.normalize(b) for b in processed_batches]

        return processed_batches
