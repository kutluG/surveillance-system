#!/usr/bin/env python3
"""
Model Quantization Pipeline for Edge Service

This script provides model quantization capabilities to reduce model size and improve
inference speed for edge deployment. It uses ONNX Runtime's quantization APIs to
convert full-precision models to INT8 quantized versions.

Features:
- Dynamic quantization using ONNX Runtime's quantize_dynamic API
- Support for models with Opset >= 13
- Comprehensive logging of quantization statistics
- Model size reduction reporting
- Validation of quantized model integrity

Usage:
    python tools/quantize_model.py [--input-model MODEL_PATH] [--output-model OUTPUT_PATH]

Requirements:
    - onnxruntime >= 1.16.0
    - onnx >= 1.14.0
    - numpy >= 1.21.0
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Third-party imports
import numpy as np

try:
    import onnx
    import onnxruntime as ort
    from onnxruntime.quantization import quantize_dynamic, QuantType
    from onnxruntime.quantization.calibrate import CalibrationDataReader
except ImportError as e:
    print(f"Error: Required quantization libraries not installed: {e}")
    print("Please install: pip install onnxruntime onnx")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelQuantizer:
    """
    Model quantization pipeline for edge deployment optimization.
    
    This class handles the conversion of full-precision ONNX models to INT8
    quantized versions using ONNX Runtime's dynamic quantization capabilities.
    """
    
    def __init__(self, model_dir: str = "/app/models"):
        """
        Initialize the model quantizer.
        
        :param model_dir: Directory containing model files
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Default model paths
        self.input_model_path = self.model_dir / "model.onnx"
        self.output_model_path = self.model_dir / "model_int8.onnx"
        
        logger.info(f"Initialized quantizer with model directory: {self.model_dir}")
    
    def check_model_compatibility(self, model_path: Path) -> bool:
        """
        Check if the model is compatible with quantization.
        
        :param model_path: Path to the ONNX model file
        :return: True if compatible, False otherwise
        """
        try:
            model = onnx.load(str(model_path))
            opset_version = model.opset_import[0].version
            
            if opset_version < 13:
                logger.warning(f"Model opset version {opset_version} < 13. Quantization may not work optimally.")
                return False
            
            logger.info(f"Model opset version: {opset_version} - Compatible with quantization")
            return True
            
        except Exception as e:
            logger.error(f"Error checking model compatibility: {e}")
            return False
    
    def get_model_size(self, model_path: Path) -> int:
        """
        Get the size of a model file in bytes.
        
        :param model_path: Path to the model file
        :return: File size in bytes
        """
        try:
            return model_path.stat().st_size
        except Exception as e:
            logger.error(f"Error getting model size: {e}")
            return 0
    
    def validate_quantized_model(self, original_path: Path, quantized_path: Path) -> Dict[str, Any]:
        """
        Validate the quantized model by comparing basic properties.
        
        :param original_path: Path to original model
        :param quantized_path: Path to quantized model
        :return: Validation results dictionary
        """
        results = {
            "valid": False,
            "original_size": 0,
            "quantized_size": 0,
            "size_reduction": 0.0,
            "compression_ratio": 0.0,
            "errors": []
        }
        
        try:
            # Get file sizes
            original_size = self.get_model_size(original_path)
            quantized_size = self.get_model_size(quantized_path)
            
            results["original_size"] = original_size
            results["quantized_size"] = quantized_size
            
            if original_size > 0:
                results["size_reduction"] = (original_size - quantized_size) / original_size
                results["compression_ratio"] = original_size / quantized_size if quantized_size > 0 else 0
            
            # Try to load both models
            try:
                original_model = onnx.load(str(original_path))
                quantized_model = onnx.load(str(quantized_path))
                
                # Basic structural validation
                if len(original_model.graph.input) != len(quantized_model.graph.input):
                    results["errors"].append("Input count mismatch")
                
                if len(original_model.graph.output) != len(quantized_model.graph.output):
                    results["errors"].append("Output count mismatch")
                  # Check if quantized model is loadable by ONNX Runtime
                try:
                    ort.InferenceSession(str(quantized_path), providers=['CPUExecutionProvider'])
                    logger.info("Quantized model successfully loaded by ONNX Runtime")
                except Exception as e:
                    results["errors"].append(f"ONNX Runtime loading error: {e}")
                
                if not results["errors"]:
                    results["valid"] = True
                    
            except Exception as e:
                results["errors"].append(f"Model loading error: {e}")
                
        except Exception as e:
            results["errors"].append(f"Validation error: {e}")
        
        return results
    
    def quantize_model(self, input_path: Optional[Path] = None, 
                      output_path: Optional[Path] = None,
                      quantization_mode: str = "IntegerOps") -> bool:
        """
        Quantize a model using ONNX Runtime's dynamic quantization.
        
        Uses ONNX Runtime's quantize_dynamic API (Opset >= 13) to produce 
        an INT8 quantized model with significant size reduction and improved
        inference speed for edge deployment.
        
        :param input_path: Path to input ONNX model (uses default if None)
        :param output_path: Path for output quantized model (uses default if None)
        :param quantization_mode: Quantization mode ('IntegerOps' or 'QLinearOps')
        :return: True if quantization successful, False otherwise
        """
        # Use provided paths or defaults
        input_model = input_path or self.input_model_path
        output_model = output_path or self.output_model_path
        
        if not input_model.exists():
            logger.error(f"Input model not found: {input_model}")
            return False
        
        logger.info(f"Starting quantization of {input_model}")
        logger.info(f"Output will be saved to: {output_model}")
        
        # Check model compatibility
        if not self.check_model_compatibility(input_model):
            logger.warning("Model may not be optimal for quantization, but proceeding...")
        
        try:
            # Configure quantization parameters for optimal edge performance
            quantization_params = {
                'model_input': str(input_model),
                'model_output': str(output_model),
                'weight_type': QuantType.QInt8,  # INT8 quantization for weights
                'optimize_model': True,  # Apply graph optimizations
                'per_channel': True,  # Per-channel quantization for better accuracy
                'reduce_range': True,  # Reduce quantization range for better compatibility
            }
            
            # Set activation quantization based on mode
            if quantization_mode == "IntegerOps":
                quantization_params['activation_type'] = QuantType.QInt8
            else:
                quantization_params['activation_type'] = QuantType.QUInt8
            
            logger.info(f"Quantization parameters: {quantization_params}")
            
            # Perform dynamic quantization
            quantize_dynamic(**quantization_params)
            
            logger.info("Quantization completed successfully")
            
            # Validate the quantized model
            validation_results = self.validate_quantized_model(input_model, output_model)
            
            if validation_results["valid"]:
                logger.info("Quantized model validation passed")
                self.log_quantization_statistics(validation_results)
            else:
                logger.error(f"Quantized model validation failed: {validation_results['errors']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return False
    
    def log_quantization_statistics(self, results: Dict[str, Any]) -> None:
        """
        Log comprehensive quantization statistics.
        
        :param results: Validation results containing size and performance metrics
        """
        original_size_mb = results["original_size"] / (1024 * 1024)
        quantized_size_mb = results["quantized_size"] / (1024 * 1024)
        size_reduction_percent = results["size_reduction"] * 100
        
        logger.info("=" * 60)
        logger.info("QUANTIZATION STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Original model size: {original_size_mb:.2f} MB")
        logger.info(f"Quantized model size: {quantized_size_mb:.2f} MB")
        logger.info(f"Size reduction: {size_reduction_percent:.1f}%")
        logger.info(f"Compression ratio: {results['compression_ratio']:.2f}x")
        logger.info("=" * 60)
        
        # Save statistics to JSON file
        stats_file = self.model_dir / "quantization_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Statistics saved to: {stats_file}")


def create_dummy_model_if_missing(model_path: Path) -> bool:
    """
    Create a dummy ONNX model for testing if the target model doesn't exist.
    
    :param model_path: Path where the model should be created
    :return: True if model was created or exists, False otherwise
    """
    if model_path.exists():
        return True
    
    logger.info(f"Creating dummy model for testing at: {model_path}")
    
    try:
        # Create a simple linear model for testing
        import onnx.helper as helper
        import onnx.numpy_helper as numpy_helper
        
        # Model parameters
        input_size = 224 * 224 * 3  # Typical image input
        hidden_size = 512
        output_size = 10  # Number of classes
        
        # Create weight tensors
        W1 = numpy_helper.from_array(
            np.random.randn(input_size, hidden_size).astype(np.float32), 
            name="W1"
        )
        b1 = numpy_helper.from_array(
            np.random.randn(hidden_size).astype(np.float32), 
            name="b1"
        )
        W2 = numpy_helper.from_array(
            np.random.randn(hidden_size, output_size).astype(np.float32),
            name="W2"
        )
        b2 = numpy_helper.from_array(
            np.random.randn(output_size).astype(np.float32),
            name="b2"
        )
        
        # Create the computational graph
        graph_def = helper.make_graph(
            [
                helper.make_node("MatMul", ["X", "W1"], ["hidden"]),
                helper.make_node("Add", ["hidden", "b1"], ["hidden_bias"]),
                helper.make_node("Relu", ["hidden_bias"], ["relu_out"]),
                helper.make_node("MatMul", ["relu_out", "W2"], ["output"]),
                helper.make_node("Add", ["output", "b2"], ["Y"]),
            ],
            "simple_classifier",
            [helper.make_tensor_value_info("X", onnx.TensorProto.FLOAT, [1, input_size])],
            [helper.make_tensor_value_info("Y", onnx.TensorProto.FLOAT, [1, output_size])],
            [W1, b1, W2, b2]
        )
        
        # Create model
        model_def = helper.make_model(graph_def, producer_name="quantization_test")
        model_def.opset_import[0].version = 13  # Set opset version for quantization compatibility
        
        # Save model
        model_path.parent.mkdir(parents=True, exist_ok=True)
        onnx.save(model_def, str(model_path))
        
        logger.info(f"Dummy model created successfully: {model_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create dummy model: {e}")
        return False


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Model Quantization Pipeline for Edge Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quantize default model
    python tools/quantize_model.py
    
    # Quantize specific model
    python tools/quantize_model.py --input-model /path/to/model.onnx --output-model /path/to/quantized.onnx
    
    # Create dummy model for testing
    python tools/quantize_model.py --create-dummy
        """
    )
    
    parser.add_argument(
        "--input-model",
        type=str,
        help="Path to input ONNX model (default: /app/models/model.onnx)"
    )
    
    parser.add_argument(
        "--output-model", 
        type=str,
        help="Path for output quantized model (default: /app/models/model_int8.onnx)"
    )
    
    parser.add_argument(
        "--model-dir",
        type=str,
        default="/app/models",
        help="Model directory (default: /app/models)"
    )
    
    parser.add_argument(
        "--quantization-mode",
        choices=["IntegerOps", "QLinearOps"],
        default="IntegerOps",
        help="Quantization mode (default: IntegerOps)"
    )
    
    parser.add_argument(
        "--create-dummy",
        action="store_true",
        help="Create a dummy model for testing if input model doesn't exist"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize quantizer
    quantizer = ModelQuantizer(model_dir=args.model_dir)
    
    # Set input/output paths
    input_path = Path(args.input_model) if args.input_model else quantizer.input_model_path
    output_path = Path(args.output_model) if args.output_model else quantizer.output_model_path
    
    # Create dummy model if requested and input doesn't exist
    if args.create_dummy and not input_path.exists():
        if not create_dummy_model_if_missing(input_path):
            logger.error("Failed to create dummy model")
            sys.exit(1)
    
    # Perform quantization
    success = quantizer.quantize_model(
        input_path=input_path,
        output_path=output_path,
        quantization_mode=args.quantization_mode
    )
    
    if success:
        logger.info("Model quantization completed successfully!")
        sys.exit(0)
    else:
        logger.error("Model quantization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
