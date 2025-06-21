"""
Frame Preprocessing Module for Edge AI Service

This module provides essential image preprocessing utilities for the edge AI service,
focusing on frame capture, resizing, normalization, and format conversion operations
required for deep learning inference.

The preprocessing pipeline ensures that input frames from various camera sources
are standardized to the format expected by TensorRT inference engines, including:
- Aspect ratio preservation through letterboxing
- Normalization with model-specific mean and standard deviation
- Color space conversion (BGR to RGB)
- Tensor format conversion (HWC to CHW)

Key Features:
    - Letterbox resizing to maintain aspect ratios while fitting target dimensions
    - Configurable normalization parameters for different model architectures
    - Efficient tensor operations using NumPy for minimal overhead
    - Support for various input image formats through OpenCV integration

Dependencies:
    - OpenCV (cv2) for image operations and color space conversions
    - NumPy for efficient tensor manipulations and mathematical operations

Author: Edge AI Service Team
Version: 1.0.0
"""
import cv2
import numpy as np
from typing import Tuple, List


def resize_letterbox(
    image: np.ndarray, target_size: Tuple[int, int]
) -> np.ndarray:
    """
    Resize and pad (letterbox) an image to the target size while preserving aspect ratio.
    
    This function implements letterboxing, which scales the image to fit within the target
    dimensions while maintaining the original aspect ratio. The remaining space is filled
    with black padding, ensuring no image distortion occurs during preprocessing.
    
    The letterboxing process:
    1. Calculate optimal scale factor to fit image within target bounds
    2. Resize image using the scale factor with linear interpolation
    3. Calculate padding needed to reach exact target dimensions
    4. Add symmetric black padding around the resized image
    
    :param image: Input BGR image as numpy array with shape (H, W, C)
    :param target_size: Target dimensions as (width, height) tuple
    :return: Letterboxed image with exact target dimensions and preserved aspect ratio
    :raises ValueError: If image is empty or target_size contains non-positive values
    """
    # Extract source and target dimensions
    src_h, src_w = image.shape[:2]
    tgt_w, tgt_h = target_size
    
    # Validate inputs
    if src_h <= 0 or src_w <= 0:
        raise ValueError("Input image has invalid dimensions")
    if tgt_w <= 0 or tgt_h <= 0:
        raise ValueError("Target size must contain positive values")
    
    # Compute scale factor to fit image within target bounds
    # Use minimum scale to ensure both dimensions fit
    scale = min(tgt_w / src_w, tgt_h / src_h)
    
    # Calculate new dimensions after scaling
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    
    # Resize image using linear interpolation for good quality/speed balance
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Calculate padding needed to reach target dimensions
    pad_w = tgt_w - new_w  # Horizontal padding needed
    pad_h = tgt_h - new_h  # Vertical padding needed
    
    # Distribute padding symmetrically around the image
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    
    # Apply letterbox padding with black color (0, 0, 0)
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
    
    This function performs comprehensive image normalization required for deep learning
    inference, including format conversion, normalization, and tensor reshaping.
    The normalization process standardizes pixel values to match the distribution
    expected by the trained model.
    
    Processing steps:
    1. Convert pixel values from uint8 [0, 255] to float32 [0, 1]
    2. Convert color space from BGR to RGB (if model expects RGB)
    3. Apply mean subtraction and standard deviation scaling
    4. Convert from HWC (Height, Width, Channels) to CHW (Channels, Height, Width)
    
    :param image: Input BGR image with pixel values in range [0, 255]
    :param mean: List of 3 mean values for R, G, B channels (in RGB order)
    :param std: List of 3 standard deviation values for R, G, B channels (in RGB order)
    :return: Normalized image in CHW format as float32 tensor
    :raises ValueError: If image dimensions don't match expected format or normalization parameters are invalid
    """
    # Validate input parameters
    if len(mean) != 3 or len(std) != 3:
        raise ValueError("Mean and std must contain exactly 3 values for RGB channels")
    if any(s <= 0 for s in std):
        raise ValueError("Standard deviation values must be positive")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be 3-channel (H, W, 3)")
    
    # Convert from uint8 [0, 255] to float32 [0, 1]
    img = image.astype(np.float32) / 255.0
    
    # Convert BGR to RGB for models trained on RGB data
    # OpenCV uses BGR by default, but most models expect RGB
    img = img[..., ::-1]  # Reverse channel order: BGR -> RGB
    
    # Convert lists to numpy arrays for vectorized operations
    mean = np.array(mean, dtype=np.float32)
    std = np.array(std, dtype=np.float32)
    
    # Apply normalization: (pixel - mean) / std
    # This centers the data around 0 and scales to unit variance
    img = (img - mean) / std
    
    # Convert from HWC to CHW format expected by most deep learning frameworks
    # (Height, Width, Channels) -> (Channels, Height, Width)
    img = np.transpose(img, (2, 0, 1))
    
    return img