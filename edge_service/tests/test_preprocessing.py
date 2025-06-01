import numpy as np
import cv2
import pytest
from preprocessing import resize_letterbox, normalize_image

def test_resize_letterbox_aspect_ratio():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = resize_letterbox(img, (224, 224))
    assert out.shape == (224, 224, 3)
    # Check letterbox padding is black
    assert np.all(out[0:10, 0:10] == 0)

def test_normalize_image_values():
    img = np.ones((224, 224, 3), dtype=np.uint8) * 255
    mean = [0.5, 0.5, 0.5]
    std = [0.5, 0.5, 0.5]
    norm = normalize_image(img, mean, std)
    # After normalization all values should be (1.0 - 0.5)/0.5 = 1.0
    assert norm.dtype == np.float32
    assert np.allclose(norm, 1.0, atol=1e-6)