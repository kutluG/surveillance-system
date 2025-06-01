"""
Frame capture and preprocessing utilities for the Edge AI Service.
"""
import cv2
import numpy as np
from typing import Tuple, List

def resize_letterbox(
    image: np.ndarray, target_size: Tuple[int, int]
) -> np.ndarray:
    """
    Resize and pad (letterbox) an image to the target size while preserving aspect ratio.
    :param image: Input BGR image as numpy array.
    :param target_size: (width, height) tuple.
    :return: Letterboxed image.
    """
    src_h, src_w = image.shape[:2]
    tgt_w, tgt_h = target_size
    # Compute scale and padding
    scale = min(tgt_w / src_w, tgt_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    # Compute padding
    pad_w = tgt_w - new_w
    pad_h = tgt_h - new_h
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    # Letterbox
    padded = cv2.copyMakeBorder(
        resized, top, bottom, left, right,
        borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )
    return padded

def normalize_image(
    image: np.ndarray, mean: List[float], std: List[float]
) -> np.ndarray:
    """
    Normalize an image by mean and standard deviation, convert to float32.
    Expects image in BGR order with pixel range [0, 255].
    :param image: Input BGR image.
    :param mean: List of 3 means for B, G, R channels.
    :param std: List of 3 stds for B, G, R channels.
    :return: Normalized image in CHW order as float32.
    """
    img = image.astype(np.float32) / 255.0
    # Convert BGR to RGB if model expects RGB; adjust here as needed
    img = img[..., ::-1]
    # Normalize
    img -= mean
    img /= std
    # HWC to CHW
    img = np.transpose(img, (2, 0, 1))
    return img