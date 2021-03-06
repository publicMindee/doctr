# Copyright (C) 2021, Mindee.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

import os
import json
import math
import tensorflow as tf
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Callable

from .core import AbstractDataset

__all__ = ["DetectionDataset"]


class DetectionDataset(AbstractDataset):
    """Implements a text detection dataset

    Example::
        >>> from doctr.datasets import DetectionDataset
        >>> train_set = DetectionDataset(img_folder=True, label_folder="/path/to/label_folder")
        >>> img, target = train_set[0]

    Args:
        img_folder: folder with all the images of the dataset
        label_folder: folder with all the corresponding labels (stem needs to be identical)
        sample_transforms: composable transformations that will be applied to each image
    """
    def __init__(
        self,
        img_folder: str,
        label_folder: str,
        sample_transforms: Optional[Callable[[tf.Tensor], tf.Tensor]] = None,
    ) -> None:
        self.sample_transforms = (lambda x: x) if sample_transforms is None else sample_transforms
        self.root = img_folder

        self.data: List[Tuple[str, Dict[str, Any]]] = []
        for img_path in os.listdir(self.root):
            with open(os.path.join(label_folder, img_path + '.json'), 'rb') as f:
                boxes = json.load(f)

            bboxes = np.asarray(boxes["boxes_1"] + boxes["boxes_2"] + boxes["boxes_3"], dtype=np.float32)
            # Switch to xmin, ymin, xmax, ymax
            bboxes = np.concatenate((bboxes.min(axis=1), bboxes.max(axis=1)), axis=1)

            is_ambiguous = [False] * (len(boxes["boxes_1"]) + len(boxes["boxes_2"])) + [True] * len(boxes["boxes_3"])

            self.data.append((img_path, dict(boxes=bboxes, flags=np.asarray(is_ambiguous))))

    def __getitem__(
        self,
        index: int
    ) -> Tuple[tf.Tensor, Dict[str, np.ndarray]]:

        img_name, target = self.data[index]
        img = tf.io.read_file(os.path.join(self.root, img_name))
        img = tf.image.decode_jpeg(img, channels=3)
        h, w = img.shape[:2]
        img = self.sample_transforms(img)

        # Boxes
        boxes = target['boxes'].copy()
        boxes[..., [0, 2]] /= w
        boxes[..., [1, 3]] /= h

        return img, dict(boxes=boxes, flags=target['flags'])

    @staticmethod
    def collate_fn(
        samples: List[Tuple[tf.Tensor, Dict[str, np.ndarray]]]
    ) -> Tuple[tf.Tensor, List[Dict[str, np.ndarray]]]:

        images, targets = zip(*samples)
        images = tf.stack(images, axis=0)

        return images, list(targets)
