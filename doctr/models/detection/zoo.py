# Copyright (C) 2021, Mindee.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

from typing import Dict, Any
from .core import DetectionPredictor, DetectionPreProcessor
from .. import detection


__all__ = ["detection_predictor"]

default_cfgs: Dict[str, Dict[str, Any]] = {
    'db_resnet50': {'model': 'db_resnet50', 'post_processor': 'DBPostProcessor'},
    'linknet': {'model': 'linknet', 'post_processor': 'LinkNetPostProcessor'},
}


def _predictor(arch: str, pretrained: bool, **kwargs: Any) -> DetectionPredictor:

    if default_cfgs.get(arch) is None:
        raise ValueError(f"unknown architecture '{arch}'")

    # Detection
    _model = detection.__dict__[default_cfgs[arch]['model']](pretrained=pretrained)
    kwargs['mean'] = kwargs.get('mean', _model.cfg['mean'])
    kwargs['std'] = kwargs.get('std', _model.cfg['std'])
    predictor = DetectionPredictor(
        DetectionPreProcessor(output_size=_model.cfg['input_shape'][:2], **kwargs),
        _model,
        detection.__dict__[default_cfgs[arch]['post_processor']]()
    )
    return predictor


def detection_predictor(arch: str = 'db_resnet50', pretrained: bool = False, **kwargs: Any) -> DetectionPredictor:
    """Text detection architecture.

    Example::
        >>> import numpy as np
        >>> from doctr.models import detection_predictor
        >>> model = detection_predictor(pretrained=True)
        >>> input_page = (255 * np.random.rand(600, 800, 3)).astype(np.uint8)
        >>> out = model([input_page])

    Args:
        arch: name of the architecture to use ('db_resnet50')
        pretrained: If True, returns a model pre-trained on our text detection dataset

    Returns:
        Detection predictor
    """

    return _predictor(arch, pretrained, **kwargs)
