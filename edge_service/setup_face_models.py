#!/usr/bin/env python3
"""
Face Detection Models Setup Script

This script downloads the required face detection models for the Edge Service.
Run this script before starting the service to ensure all models are available.
"""

import os
import hashlib
import requests
from pathlib import Path
import argparse

# Model configurations
MODEL_CONFIGS = {
    'haar_cascade': {
        'url': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml',
        'filename': 'haarcascade_frontalface_default.xml',
        'description': 'Haar Cascade frontal face detector',
        'size_mb': 0.93,
        'sha256': 'None'  # Will be calculated on first download
    },
    'dnn_prototxt': {
        'url': 'https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/opencv_face_detector.pbtxt',
        'filename': 'opencv_face_detector.pbtxt',
        'description': 'OpenCV DNN face detector prototxt',
        'size_mb': 0.01,
        'sha256': 'None'
    },
    'dnn_model': {
        'url': 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb',
        'filename': 'opencv_face_detector_uint8.pb',
        'description': 'OpenCV DNN face detector model weights',
        'size_mb': 2.7,
        'sha256': 'None'
    }
}

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def download_file(url, file_path, description="file"):
    """Download a file with progress indication"""
    print(f"📥 Downloading {description}...")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r  Progress: {progress:.1f}% ({downloaded}/{total_size} bytes)", end='')
        
        print()  # New line after progress
        return True
        
    except Exception as e:
        print(f"❌ Failed to download {description}: {e}")
        if file_path.exists():
            file_path.unlink()
        return False

def verify_model_file(file_path, expected_size_mb=None):
    """Verify that a model file is valid"""
    if not file_path.exists():
        return False, "File does not exist"
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    
    if expected_size_mb and abs(file_size_mb - expected_size_mb) > 0.1:
        return False, f"Size mismatch: expected ~{expected_size_mb}MB, got {file_size_mb:.2f}MB"
    
    # Basic file integrity check
    try:
        with open(file_path, 'rb') as f:
            header = f.read(100)
            if len(header) == 0:
                return False, "File is empty"
    except Exception as e:
        return False, f"Cannot read file: {e}"
    
    return True, "OK"

def setup_model(model_name, config, model_dir, force=False):
    """Download and setup a single model"""
    file_path = model_dir / config['filename']
    
    # Check if file already exists and is valid
    if file_path.exists() and not force:
        is_valid, message = verify_model_file(file_path, config['size_mb'])
        if is_valid:
            print(f"✓ {config['description']} already exists and is valid")
            return True
        else:
            print(f"⚠ {config['description']} exists but is invalid: {message}")
            print(f"  Removing and re-downloading...")
            file_path.unlink()
    
    # Download the model
    success = download_file(config['url'], file_path, config['description'])
    
    if success:
        # Verify the downloaded file
        is_valid, message = verify_model_file(file_path, config['size_mb'])
        if is_valid:
            # Calculate and store hash for future verification
            file_hash = calculate_file_hash(file_path)
            print(f"✓ {config['description']} downloaded successfully")
            print(f"  Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"  SHA256: {file_hash[:16]}...")
            return True
        else:
            print(f"❌ Downloaded file is invalid: {message}")
            file_path.unlink()
            return False
    
    return False

def setup_all_models(model_dir='/models', force=False):
    """Download all required face detection models"""
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Setting up face detection models in {model_dir}")
    print("=" * 60)
    
    success_count = 0
    total_models = len(MODEL_CONFIGS)
    
    for model_name, config in MODEL_CONFIGS.items():
        print(f"\n[{success_count + 1}/{total_models}] Setting up {model_name}")
        print("-" * 40)
        
        if setup_model(model_name, config, model_dir, force):
            success_count += 1
        else:
            print(f"❌ Failed to setup {model_name}")
    
    print("\n" + "=" * 60)
    print(f"Model setup complete: {success_count}/{total_models} successful")
    
    if success_count == total_models:
        print("✅ All face detection models are ready!")
        print("\nNext steps:")
        print("1. Verify models are in the correct location")
        print("2. Set MODEL_DIR environment variable if needed")
        print("3. Start the Edge Service")
        return True
    else:
        print("⚠ Some models failed to download. The service may not work properly.")
        print("\nTroubleshooting:")
        print("- Check internet connection")
        print("- Verify write permissions to model directory")
        print("- Try running with --force to re-download all models")
        return False

def list_models(model_dir='/models'):
    """List all models in the model directory"""
    model_dir = Path(model_dir)
    
    if not model_dir.exists():
        print(f"Model directory {model_dir} does not exist")
        return
    
    print(f"Models in {model_dir}:")
    print("-" * 40)
    
    for model_name, config in MODEL_CONFIGS.items():
        file_path = model_dir / config['filename']
        
        if file_path.exists():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            is_valid, message = verify_model_file(file_path, config['size_mb'])
            status = "✓ Valid" if is_valid else f"❌ Invalid: {message}"
            print(f"{config['filename']}: {file_size_mb:.2f} MB - {status}")
        else:
            print(f"{config['filename']}: ❌ Not found")

def main():
    """
    Main entry point for face model setup utility.
    
    Provides a command-line interface for downloading, verifying, and managing
    face detection models required by the edge service. Handles model downloads
    with progress tracking, validation, and error recovery.
    
    :raises SystemExit: If critical errors occur during model setup
    """
    parser = argparse.ArgumentParser(
        description="Setup face detection models for Edge Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_face_models.py                    # Download to default /models
  python setup_face_models.py --dir ./models     # Download to custom directory
  python setup_face_models.py --force            # Force re-download all models
  python setup_face_models.py --list             # List existing models
        """
    )
    
    parser.add_argument(
        '--dir', 
        default='/models',
        help='Directory to store models (default: /models)'
    )
    
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force re-download even if models exist'
    )
    
    parser.add_argument(
        '--list', 
        action='store_true',
        help='List existing models and exit'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_models(args.dir)
        return
    
    print("Edge Service - Face Detection Models Setup")
    print("=" * 50)
    print(f"Target directory: {args.dir}")
    print(f"Force re-download: {args.force}")
    print()
    
    success = setup_all_models(args.dir, args.force)
    
    if success:
        print("\n🎉 Setup completed successfully!")
        exit(0)
    else:
        print("\n💥 Setup failed!")
        exit(1)

if __name__ == "__main__":
    main()
