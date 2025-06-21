"""
Edge Service Configuration Module

This module provides configuration management for the edge service,
including model download settings and face anonymization configuration.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseSettings, Field, validator
from pydantic_settings import SettingsConfigDict


class EdgeServiceSettings(BaseSettings):
    """
    Edge service configuration with environment variable support.
    
    This configuration handles model management, face anonymization,
    camera settings, and service connectivity.
    """
    
    model_config = SettingsConfigDict(
        env_prefix='EDGE_SERVICE_',
        case_sensitive=False,
        env_file='.env',
        env_file_encoding='utf-8'
    )
    
    # Model Management Configuration
    model_base_url: str = Field(
        default="https://raw.githubusercontent.com/opencv/opencv/master",
        description="Base URL for downloading face detection models"
    )
    
    model_dir: str = Field(
        default="/app/models",
        description="Directory where face detection models are stored"
    )
    
    # Face Detection Model Paths (derived from model_dir)
    haar_cascade_path: Optional[str] = Field(
        default=None,
        description="Path to Haar cascade face detection model"
    )    
    dnn_prototxt_path: Optional[str] = Field(
        default=None,
        description="Path to DNN prototxt file for face detection"
    )
    
    dnn_model_path: Optional[str] = Field(
        default=None,
        description="Path to DNN model file for face detection"
    )
    
    # Quantized Model Configuration
    quantized_model_path: Optional[str] = Field(
        default=None,
        description="Path to quantized INT8 ONNX model for optimized inference"
    )
    
    use_quantized_model: bool = Field(
        default=True,
        description="Whether to use quantized model for inference when available"
    )
    
    # Face Anonymization Configuration
    anonymization_enabled: bool = Field(
        default=True,
        description="Enable face anonymization processing"
    )
    
    privacy_level: str = Field(
        default="moderate",
        description="Privacy protection level: strict, moderate, minimal"
    )
    
    anonymization_method: str = Field(
        default="blur",
        description="Anonymization method: blur, pixelate, black_box, emoji"
    )
    
    blur_factor: int = Field(
        default=15,
        ge=5,
        le=50,
        description="Blur intensity for face anonymization"
    )
    
    pixelate_factor: int = Field(
        default=10,
        ge=5,
        le=30,
        description="Pixelation intensity for face anonymization"
    )
    
    # Camera Configuration
    camera_id: str = Field(
        default="camera-01",
        description="Unique identifier for this camera"
    )
    
    capture_device: int = Field(
        default=0,
        description="Camera device index for video capture"
    )
    
    target_resolution: str = Field(
        default="224,224",
        description="Target resolution for inference (width,height)"
    )
    
    # Image Processing Configuration
    mean: List[float] = Field(
        default=[0.485, 0.456, 0.406],
        description="Image normalization mean values"
    )
    
    std: List[float] = Field(
        default=[0.229, 0.224, 0.225],
        description="Image normalization standard deviation values"
    )
    
    # MQTT Configuration
    mqtt_broker: str = Field(
        default="mqtt.example.com",
        description="MQTT broker hostname"
    )
    
    mqtt_port: int = Field(
        default=8883,
        description="MQTT broker port"
    )
    
    mqtt_tls_ca: str = Field(
        default="/certs/ca.crt",
        description="Path to MQTT TLS CA certificate"
    )
    
    mqtt_tls_cert: str = Field(
        default="/certs/client.crt",
        description="Path to MQTT TLS client certificate"
    )
    
    mqtt_tls_key: str = Field(
        default="/certs/client.key",
        description="Path to MQTT TLS client key"
    )
    
    # Kafka Configuration (for hard examples)
    kafka_broker: str = Field(
        default="kafka:9092",
        description="Kafka broker for hard example publishing"
    )
    
    hard_example_topic: str = Field(
        default="hard-examples",
        description="Kafka topic for hard examples"
    )
    
    # Performance Configuration
    max_frames_per_second: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Maximum frames per second for processing"
    )
    
    batch_size: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Batch size for inference processing"
    )
    
    # Hard Example Detection Thresholds
    hard_example_thresholds: Dict[str, float] = Field(
        default={
            'person': 0.6,
            'face': 0.5,
            'vehicle': 0.4,
            'object': 0.5        },
        description="Confidence thresholds for hard example detection"
    )
    
    @validator('target_resolution')
    def validate_resolution(cls, v):
        """
        Validate target resolution format and ensure positive dimensions.
        
        :param v: Resolution string in format 'width,height'
        :return: Validated resolution string
        :raises ValueError: If format is invalid or dimensions are not positive
        """
        try:
            # Parse comma-separated width and height values
            width, height = map(int, v.split(','))            # Ensure both dimensions are positive integers
            if width <= 0 or height <= 0:
                raise ValueError("Resolution dimensions must be positive")
            return v
        except ValueError:
            raise ValueError("Resolution must be in format 'width,height'")
    
    @validator('privacy_level')
    def validate_privacy_level(cls, v):
        """
        Validate privacy level against allowed values.
        
        :param v: Privacy level string to validate
        :return: Validated privacy level in lowercase
        :raises ValueError: If privacy level is not in allowed values        """
        valid_levels = ['strict', 'moderate', 'minimal']
        if v.lower() not in valid_levels:
            raise ValueError(f"Privacy level must be one of: {valid_levels}")
        return v.lower()
    
    @validator('anonymization_method')
    def validate_anonymization_method(cls, v):
        """
        Validate anonymization method against supported methods.
        
        :param v: Anonymization method string to validate
        :return: Validated anonymization method in lowercase
        :raises ValueError: If method is not supported
        """
        valid_methods = ['blur', 'pixelate', 'black_box', 'emoji']
        if v.lower() not in valid_methods:
            raise ValueError(f"Anonymization method must be one of: {valid_methods}")
        return v.lower()
    
    def __init__(self, **data):
        """
        Initialize settings and set derived model file paths.
        
        This method automatically sets model file paths based on the model_dir
        if they are not explicitly provided in the configuration.
        
        :param data: Configuration data dictionary passed to parent constructor
        """
        super().__init__(**data)
        
        # Set derived model paths if not explicitly provided
        model_path = Path(self.model_dir)
        
        # Configure Haar cascade model path
        if self.haar_cascade_path is None:
            self.haar_cascade_path = str(model_path / "haarcascade_frontalface_default.xml")
        
        # Configure DNN prototxt file path
        if self.dnn_prototxt_path is None:
            self.dnn_prototxt_path = str(model_path / "opencv_face_detector.pbtxt")        # Configure DNN model binary path
        if self.dnn_model_path is None:
            self.dnn_model_path = str(model_path / "opencv_face_detector_uint8.pb")
        
        # Configure quantized model path
        if self.quantized_model_path is None:
            self.quantized_model_path = str(model_path / "model_int8.onnx")
    
    def get_target_resolution_tuple(self) -> tuple[int, int]:
        """
        Get target resolution as a tuple of integers.
        
        Parses the target_resolution string and converts it to a tuple of integers
        for use in image processing operations.
        
        :return: Tuple containing (width, height) as integers        :raises ValueError: If resolution format is invalid
        """
        width, height = self.target_resolution.split(',')
        return int(width), int(height)
    
    def get_model_download_urls(self) -> Dict[str, str]:
        """
        Get URLs for downloading face detection models.
        
        Constructs download URLs for all required face detection models
        based on the configured base URL and known model locations.
        
        :return: Dictionary mapping model names to their download URLs
        """
        base_url = self.model_base_url.rstrip('/')
        
        return {
            'haar_cascade': f"{base_url}/data/haarcascades/haarcascade_frontalface_default.xml",
            'dnn_prototxt': f"{base_url}/samples/dnn/face_detector/opencv_face_detector.pbtxt",
            'dnn_model': "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb"        }
    
    def get_anonymization_config(self) -> Dict[str, Any]:
        """
        Get anonymization configuration dictionary.
        
        Creates a comprehensive configuration dictionary containing all
        anonymization settings and model paths for use by the face
        anonymization module.
        
        :return: Dictionary containing all anonymization configuration parameters
        """
        return {
            'enabled': self.anonymization_enabled,
            'method': self.anonymization_method,
            'privacy_level': self.privacy_level,
            'blur_factor': self.blur_factor,
            'pixelate_factor': self.pixelate_factor,
            'haar_cascade_path': self.haar_cascade_path,
            'dnn_prototxt_path': self.dnn_prototxt_path,
            'dnn_model_path': self.dnn_model_path
        }


# Global settings instance
settings = EdgeServiceSettings()


def get_settings() -> EdgeServiceSettings:
    """
    Get the global settings instance.
    
    Returns the singleton instance of EdgeServiceSettings that contains
    the current configuration for the edge service.
    
    :return: Global EdgeServiceSettings instance
    """
    return settings


def reload_settings() -> EdgeServiceSettings:
    """
    Reload settings from environment variables.
    
    Creates a new instance of EdgeServiceSettings, re-reading all configuration
    from environment variables. This is useful for runtime configuration updates.
    
    :return: New EdgeServiceSettings instance with updated configuration
    """
    global settings
    settings = EdgeServiceSettings()
    return settings


def get_model_paths() -> dict:
    """
    Get all model file paths for face detection.
    
    Returns a dictionary containing paths to all required face detection
    model files and the model directory.
    
    :return: Dictionary mapping model names to their file paths
    """
    return {
        "haar_cascade": settings.haar_cascade_path,
        "dnn_prototxt": settings.dnn_prototxt_path,
        "dnn_model": settings.dnn_model_path,
        "model_dir": settings.model_dir
    }


def validate_model_files() -> bool:
    """
    Validate that all required model files exist and are not empty.
    
    Checks for the existence and size of all required face detection model files.
    This ensures the service can properly initialize before attempting to use the models.
    
    :return: True if all model files are valid, False otherwise
    """
    model_paths = get_model_paths()
    
    for model_name, path in model_paths.items():
        if model_name == "model_dir":
            # Check if model directory exists
            if not os.path.isdir(path):
                print(f"Model directory not found: {path}")
                return False
        else:
            # Check if model file exists
            if not os.path.isfile(path):
                print(f"Model file not found: {path} ({model_name})")
                return False
            
            # Check if model file is not empty
            if os.path.getsize(path) == 0:
                print(f"Model file is empty: {path} ({model_name})")
                return False
    
    return True
