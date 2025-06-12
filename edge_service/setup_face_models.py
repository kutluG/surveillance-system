#!/usr/bin/env python3
"""
Download OpenCV face detection models for face anonymization.
This script downloads the required model files for both Haar cascade and DNN-based face detection.
"""

import os
import urllib.request
import hashlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    'haar_cascade': {
        'url': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml',
        'filename': 'haarcascade_frontalface_default.xml',
        'sha256': 'dc53c086765d1d1b31b6b8d3b0e4a9e8a5e9a5e5e5e5e5e5e5e5e5e5e5e5e5e5'  # Placeholder hash
    },
    'dnn_prototxt': {
        'url': 'https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/opencv_face_detector.pbtxt',
        'filename': 'opencv_face_detector.pbtxt',
        'sha256': 'placeholder_hash'  # Placeholder hash
    },
    'dnn_model': {
        'url': 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb',
        'filename': 'opencv_face_detector_uint8.pb',
        'sha256': 'placeholder_hash'  # Placeholder hash
    }
}

def calculate_sha256(filepath):
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def download_file(url, filepath, expected_hash=None):
    """Download a file from URL to filepath with optional hash verification."""
    try:
        logger.info(f"Downloading {os.path.basename(filepath)} from {url}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Download file
        urllib.request.urlretrieve(url, filepath)
        
        # Verify file exists and has content
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise Exception(f"Downloaded file {filepath} is empty or doesn't exist")
        
        # Verify hash if provided (skip for placeholder hashes)
        if expected_hash and expected_hash != 'placeholder_hash':
            actual_hash = calculate_sha256(filepath)
            if actual_hash != expected_hash:
                logger.warning(f"Hash mismatch for {filepath}. Expected: {expected_hash}, Got: {actual_hash}")
        
        logger.info(f"Successfully downloaded {os.path.basename(filepath)} ({os.path.getsize(filepath)} bytes)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {url}: {str(e)}")
        # Clean up failed download
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def setup_models(models_dir="models"):
    """Download all required face detection models."""
    models_path = Path(models_dir)
    models_path.mkdir(exist_ok=True)
    
    logger.info(f"Setting up face detection models in {models_path.absolute()}")
    
    success_count = 0
    total_count = len(MODELS)
    
    for model_name, config in MODELS.items():
        filepath = models_path / config['filename']
        
        # Skip if file already exists and is not empty
        if filepath.exists() and filepath.stat().st_size > 0:
            logger.info(f"{config['filename']} already exists, skipping download")
            success_count += 1
            continue
        
        if download_file(config['url'], str(filepath), config.get('sha256')):
            success_count += 1
        else:
            logger.error(f"Failed to download {model_name}")
    
    if success_count == total_count:
        logger.info("All face detection models downloaded successfully!")
        
        # Create environment file with model paths
        env_content = f"""# Face detection model paths
FACE_MODEL_PATH={models_path.absolute()}
HAAR_CASCADE_PATH={models_path.absolute()}/haarcascade_frontalface_default.xml
DNN_PROTOTXT_PATH={models_path.absolute()}/opencv_face_detector.pbtxt
DNN_MODEL_PATH={models_path.absolute()}/opencv_face_detector_uint8.pb
"""
        
        env_file = models_path / "model_paths.env"
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"Model paths saved to {env_file}")
        
        return True
    else:
        logger.error(f"Only {success_count}/{total_count} models downloaded successfully")
        return False

def verify_models(models_dir="models"):
    """Verify that all required models are present and accessible."""
    models_path = Path(models_dir)
    
    if not models_path.exists():
        logger.error(f"Models directory {models_path} does not exist")
        return False
    
    logger.info("Verifying face detection models...")
    
    all_present = True
    for model_name, config in MODELS.items():
        filepath = models_path / config['filename']
        
        if not filepath.exists():
            logger.error(f"Missing model file: {filepath}")
            all_present = False
        elif filepath.stat().st_size == 0:
            logger.error(f"Empty model file: {filepath}")
            all_present = False
        else:
            logger.info(f"✓ {config['filename']} ({filepath.stat().st_size} bytes)")
    
    if all_present:
        logger.info("All face detection models are present and valid!")
        
        # Test OpenCV model loading
        try:
            import cv2
            
            # Test Haar cascade
            haar_path = str(models_path / 'haarcascade_frontalface_default.xml')
            cascade = cv2.CascadeClassifier(haar_path)
            if cascade.empty():
                logger.error("Failed to load Haar cascade classifier")
                all_present = False
            else:
                logger.info("✓ Haar cascade classifier loads successfully")
            
            # Test DNN model
            prototxt_path = str(models_path / 'opencv_face_detector.pbtxt')
            model_path = str(models_path / 'opencv_face_detector_uint8.pb')
            
            if Path(prototxt_path).exists() and Path(model_path).exists():
                try:
                    net = cv2.dnn.readNetFromTensorflow(model_path, prototxt_path)
                    logger.info("✓ DNN face detector loads successfully")
                except Exception as e:
                    logger.warning(f"DNN model loading failed: {e}")
                    logger.info("Haar cascade will be used as fallback")
            
        except ImportError:
            logger.warning("OpenCV not available for model verification")
    
    return all_present

if __name__ == "__main__":
    import sys
    
    models_dir = sys.argv[1] if len(sys.argv) > 1 else "models"
    
    logger.info("Face Detection Models Setup Script")
    logger.info("====================================")
    
    # Setup models
    if setup_models(models_dir):
        # Verify models
        if verify_models(models_dir):
            logger.info("Face detection models setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("Model verification failed")
            sys.exit(1)
    else:
        logger.error("Model setup failed")
        sys.exit(1)
