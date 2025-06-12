#!/usr/bin/env python3
"""
TensorRT Model Conversion and Optimization for Edge Deployment

This script converts ONNX models to TensorRT format for optimized edge inference:
1. Downloads models from MLflow Model Registry
2. Converts ONNX to TensorRT with optimization
3. Benchmarks inference performance
4. Logs optimized models back to MLflow

Usage:
    python train/convert_to_trt.py --model-name surveillance_mobilenet_v3_edge --version 1
    python train/convert_to_trt.py --run-id abc123def456 --precision fp16
    python train/convert_to_trt.py --model-uri runs:/abc123/pytorch_model --batch-size 8

Environment Variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URI
    TRT_CACHE_DIR: TensorRT engine cache directory
    CUDA_VISIBLE_DEVICES: GPU device selection
"""

import os
import sys
import json
import argparse
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# MLflow imports
try:
    import mlflow
    import mlflow.pytorch
    from mlflow.tracking import MlflowClient
    from mlflow.entities.model_registry import ModelVersion
except ImportError:
    print("ERROR: MLflow not installed. Run: pip install mlflow")
    sys.exit(1)

# TensorRT and ONNX imports
try:
    import tensorrt as trt
    import onnx
    import onnxruntime as ort
    import pycuda.driver as cuda
    import pycuda.autoinit
except ImportError as e:
    print(f"ERROR: TensorRT/CUDA dependencies missing: {e}")
    print("Install TensorRT following NVIDIA documentation")
    print("Install with: pip install onnx onnxruntime-gpu pycuda")
    sys.exit(1)

# Additional dependencies
try:
    import numpy as np
    import cv2
    import torch
    from PIL import Image
    import psutil
    import GPUtil
except ImportError as e:
    print(f"ERROR: Additional dependencies missing: {e}")
    print("Install with: pip install numpy opencv-python torch pillow psutil gputil")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tensorrt_converter')

# TensorRT Logger
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

class TensorRTConverter:
    """TensorRT model converter with MLflow integration"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.client = MlflowClient()
        self.cache_dir = Path(os.getenv('TRT_CACHE_DIR', 'cache/tensorrt'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup MLflow tracking
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        
        # Check GPU availability
        self._check_gpu_availability()
    
    def _check_gpu_availability(self):
        """Check GPU and TensorRT compatibility"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                raise RuntimeError("No GPU detected. TensorRT requires CUDA-compatible GPU.")
            
            gpu = gpus[0]
            logger.info(f"GPU detected: {gpu.name}")
            logger.info(f"GPU Memory: {gpu.memoryTotal:.0f}MB total, {gpu.memoryFree:.0f}MB free")
            
            # Check CUDA version
            cuda_version = torch.version.cuda
            logger.info(f"CUDA Version: {cuda_version}")
            
            # Check TensorRT version
            trt_version = trt.__version__
            logger.info(f"TensorRT Version: {trt_version}")
            
        except Exception as e:
            logger.error(f"GPU/TensorRT check failed: {e}")
            raise
    
    def download_model(self) -> str:
        """Download ONNX model from MLflow"""
        if self.args.model_uri:
            # Direct model URI
            model_uri = self.args.model_uri
            
        elif self.args.run_id:
            # Model from specific run
            model_uri = f"runs:/{self.args.run_id}/pytorch_model"
            
        elif self.args.model_name:
            # Model from registry
            if self.args.version:
                model_uri = f"models:/{self.args.model_name}/{self.args.version}"
            else:
                # Get latest version
                latest_version = self.client.get_latest_versions(
                    self.args.model_name, 
                    stages=["Production", "Staging"]
                )[0]
                model_uri = f"models:/{self.args.model_name}/{latest_version.version}"
                logger.info(f"Using latest version: {latest_version.version}")
        
        else:
            raise ValueError("Must specify --model-uri, --run-id, or --model-name")
        
        logger.info(f"Downloading model from: {model_uri}")
        
        # Download model artifacts
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = mlflow.artifacts.download_artifacts(
                artifact_uri=model_uri,
                dst_path=temp_dir
            )
            
            # Look for ONNX file
            onnx_files = list(Path(model_path).rglob("*.onnx"))
            if not onnx_files:
                raise FileNotFoundError(f"No ONNX file found in model artifacts: {model_path}")
            
            onnx_path = str(onnx_files[0])
            
            # Copy to cache directory for persistence
            cache_file = self.cache_dir / f"model_{int(time.time())}.onnx"
            import shutil
            shutil.copy2(onnx_path, cache_file)
            
            logger.info(f"✅ Model downloaded: {cache_file}")
            return str(cache_file)
    
    def build_trt_engine(self, onnx_path: str) -> str:
        """Build TensorRT engine from ONNX model"""
        engine_path = onnx_path.replace('.onnx', f'_{self.args.precision}_batch{self.args.max_batch_size}.engine')
        
        # Check if engine already exists
        if os.path.exists(engine_path) and not self.args.force_rebuild:
            logger.info(f"TensorRT engine already exists: {engine_path}")
            return engine_path
        
        logger.info(f"Building TensorRT engine from {onnx_path}")
        logger.info(f"Precision: {self.args.precision}")
        logger.info(f"Max batch size: {self.args.max_batch_size}")
        logger.info(f"Max workspace size: {self.args.max_workspace_size}GB")
        
        # Create TensorRT builder
        builder = trt.Builder(TRT_LOGGER)
        config = builder.create_builder_config()
        
        # Set precision
        if self.args.precision == 'fp16':
            if not builder.platform_has_fast_fp16:
                logger.warning("FP16 not supported on this platform, falling back to FP32")
            else:
                config.set_flag(trt.BuilderFlag.FP16)
                logger.info("✅ FP16 precision enabled")
        
        elif self.args.precision == 'int8':
            if not builder.platform_has_fast_int8:
                logger.warning("INT8 not supported on this platform, falling back to FP32")
            else:
                config.set_flag(trt.BuilderFlag.INT8)
                # Note: INT8 calibration would be needed for production
                logger.info("✅ INT8 precision enabled (without calibration)")
        
        # Set memory pool
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, self.args.max_workspace_size * 1024**3)
        
        # Enable optimization profiles for dynamic shapes
        profile = builder.create_optimization_profile()
        
        # Parse ONNX model
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        with open(onnx_path, 'rb') as model_file:
            if not parser.parse(model_file.read()):
                logger.error("Failed to parse ONNX model")
                for error in range(parser.num_errors):
                    logger.error(f"Parser error {error}: {parser.get_error(error)}")
                raise RuntimeError("ONNX parsing failed")
        
        # Configure dynamic shapes
        input_tensor = network.get_input(0)
        input_shape = input_tensor.shape
        
        logger.info(f"Input shape: {input_shape}")
        
        # Set optimization profile for batch dimension
        min_shape = [1] + list(input_shape[1:])
        opt_shape = [self.args.max_batch_size // 2] + list(input_shape[1:])
        max_shape = [self.args.max_batch_size] + list(input_shape[1:])
        
        profile.set_shape(input_tensor.name, min_shape, opt_shape, max_shape)
        config.add_optimization_profile(profile)
        
        # Build engine
        logger.info("Building TensorRT engine... This may take several minutes.")
        start_time = time.time()
        
        engine = builder.build_serialized_network(network, config)
        
        if engine is None:
            raise RuntimeError("Failed to build TensorRT engine")
        
        build_time = time.time() - start_time
        logger.info(f"✅ Engine built successfully in {build_time:.2f} seconds")
        
        # Save engine to file
        with open(engine_path, 'wb') as f:
            f.write(engine)
        
        logger.info(f"✅ TensorRT engine saved: {engine_path}")
        
        return engine_path
    
    def benchmark_model(self, engine_path: str, onnx_path: str) -> Dict[str, Any]:
        """Benchmark TensorRT vs ONNX performance"""
        logger.info("Starting performance benchmark...")
        
        # Load TensorRT engine
        runtime = trt.Runtime(TRT_LOGGER)
        with open(engine_path, 'rb') as f:
            engine = runtime.deserialize_cuda_engine(f.read())
        
        context = engine.create_execution_context()
        
        # Get input/output shapes
        input_shape = engine.get_binding_shape(0)
        output_shape = engine.get_binding_shape(1)
        
        logger.info(f"TensorRT input shape: {input_shape}")
        logger.info(f"TensorRT output shape: {output_shape}")
        
        # Allocate GPU memory
        input_size = trt.volume(input_shape) * engine.max_batch_size
        output_size = trt.volume(output_shape) * engine.max_batch_size
        
        h_input = np.random.randn(input_size).astype(np.float32)
        h_output = np.empty(output_size, dtype=np.float32)
        
        d_input = cuda.mem_alloc(h_input.nbytes)
        d_output = cuda.mem_alloc(h_output.nbytes)
        
        bindings = [int(d_input), int(d_output)]
        stream = cuda.Stream()
        
        # Benchmark TensorRT
        num_warmup = 10
        num_benchmark = 100
        
        # Warmup
        for _ in range(num_warmup):
            cuda.memcpy_htod_async(d_input, h_input, stream)
            context.execute_async_v2(bindings, stream.handle)
            cuda.memcpy_dtoh_async(h_output, d_output, stream)
            stream.synchronize()
        
        # Benchmark TensorRT
        start_time = time.time()
        for _ in range(num_benchmark):
            cuda.memcpy_htod_async(d_input, h_input, stream)
            context.execute_async_v2(bindings, stream.handle)
            cuda.memcpy_dtoh_async(h_output, d_output, stream)
            stream.synchronize()
        
        trt_total_time = time.time() - start_time
        trt_avg_latency = (trt_total_time / num_benchmark) * 1000  # ms
        trt_throughput = num_benchmark / trt_total_time  # fps
        
        # Benchmark ONNX Runtime
        ort_session = ort.InferenceSession(onnx_path, providers=['CUDAExecutionProvider'])
        
        input_name = ort_session.get_inputs()[0].name
        test_input = np.random.randn(1, *input_shape[1:]).astype(np.float32)
        
        # Warmup ONNX
        for _ in range(num_warmup):
            ort_session.run(None, {input_name: test_input})
        
        # Benchmark ONNX
        start_time = time.time()
        for _ in range(num_benchmark):
            ort_session.run(None, {input_name: test_input})
        
        ort_total_time = time.time() - start_time
        ort_avg_latency = (ort_total_time / num_benchmark) * 1000  # ms
        ort_throughput = num_benchmark / ort_total_time  # fps
        
        # Calculate improvements
        latency_improvement = ((ort_avg_latency - trt_avg_latency) / ort_avg_latency) * 100
        throughput_improvement = ((trt_throughput - ort_throughput) / ort_throughput) * 100
        
        # Get model sizes
        trt_size = os.path.getsize(engine_path) / (1024 * 1024)  # MB
        onnx_size = os.path.getsize(onnx_path) / (1024 * 1024)  # MB
        
        benchmark_results = {
            'tensorrt_latency_ms': trt_avg_latency,
            'tensorrt_throughput_fps': trt_throughput,
            'onnx_latency_ms': ort_avg_latency,
            'onnx_throughput_fps': ort_throughput,
            'latency_improvement_percent': latency_improvement,
            'throughput_improvement_percent': throughput_improvement,
            'tensorrt_model_size_mb': trt_size,
            'onnx_model_size_mb': onnx_size,
            'precision': self.args.precision,
            'max_batch_size': self.args.max_batch_size,
            'benchmark_iterations': num_benchmark
        }
        
        logger.info("📊 Benchmark Results:")
        logger.info(f"TensorRT Latency: {trt_avg_latency:.2f}ms")
        logger.info(f"ONNX Latency: {ort_avg_latency:.2f}ms")
        logger.info(f"Latency Improvement: {latency_improvement:.1f}%")
        logger.info(f"TensorRT Throughput: {trt_throughput:.1f} FPS")
        logger.info(f"ONNX Throughput: {ort_throughput:.1f} FPS")
        logger.info(f"Throughput Improvement: {throughput_improvement:.1f}%")
        logger.info(f"Model Size - TensorRT: {trt_size:.1f}MB, ONNX: {onnx_size:.1f}MB")
        
        # Cleanup GPU memory
        d_input.free()
        d_output.free()
        
        return benchmark_results
    
    def log_to_mlflow(self, engine_path: str, onnx_path: str, benchmark_results: Dict[str, Any]) -> str:
        """Log optimized model and metrics to MLflow"""
        
        experiment_name = "tensorrt-optimization"
        try:
            mlflow.create_experiment(experiment_name)
        except Exception:
            pass
        
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=f"trt_optimization_{self.args.precision}") as run:
            run_id = run.info.run_id
            
            # Log parameters
            mlflow.log_params({
                'source_model_uri': getattr(self.args, 'model_uri', ''),
                'source_model_name': getattr(self.args, 'model_name', ''),
                'source_run_id': getattr(self.args, 'run_id', ''),
                'tensorrt_precision': self.args.precision,
                'max_batch_size': self.args.max_batch_size,
                'max_workspace_size_gb': self.args.max_workspace_size,
                'optimization_timestamp': datetime.now().isoformat(),
                'tensorrt_version': trt.__version__,
                'cuda_version': torch.version.cuda
            })
            
            # Log benchmark metrics
            mlflow.log_metrics(benchmark_results)
            
            # Log model artifacts
            mlflow.log_artifact(engine_path, "models")
            mlflow.log_artifact(onnx_path, "models")
            
            # Create performance report
            report = {
                'optimization_summary': {
                    'latency_improvement': f"{benchmark_results['latency_improvement_percent']:.1f}%",
                    'throughput_improvement': f"{benchmark_results['throughput_improvement_percent']:.1f}%",
                    'model_size_reduction': f"{((benchmark_results['onnx_model_size_mb'] - benchmark_results['tensorrt_model_size_mb']) / benchmark_results['onnx_model_size_mb'] * 100):.1f}%"
                },
                'deployment_info': {
                    'recommended_batch_size': self.args.max_batch_size,
                    'memory_requirements_mb': benchmark_results['tensorrt_model_size_mb'],
                    'precision': self.args.precision,
                    'target_hardware': 'NVIDIA GPU with TensorRT support'
                },
                'benchmark_details': benchmark_results
            }
            
            report_path = self.cache_dir / f"optimization_report_{run_id}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            mlflow.log_artifact(str(report_path), "reports")
            
            # Register optimized model if model name provided
            if self.args.model_name:
                optimized_model_name = f"{self.args.model_name}_tensorrt_{self.args.precision}"
                
                try:
                    model_version = mlflow.register_model(
                        model_uri=f"runs:/{run_id}/models",
                        name=optimized_model_name,
                        tags={
                            "optimization": "tensorrt",
                            "precision": self.args.precision,
                            "source_model": self.args.model_name,
                            "latency_improvement": f"{benchmark_results['latency_improvement_percent']:.1f}%"
                        }
                    )
                    
                    logger.info(f"✅ Optimized model registered: {optimized_model_name} v{model_version.version}")
                    
                except Exception as e:
                    logger.warning(f"Failed to register optimized model: {e}")
            
            logger.info(f"✅ Results logged to MLflow run: {run_id}")
            return run_id
    
    def convert(self) -> str:
        """Main conversion workflow"""
        logger.info("🚀 Starting TensorRT conversion pipeline")
        
        try:
            # Download model
            onnx_path = self.download_model()
            
            # Build TensorRT engine
            engine_path = self.build_trt_engine(onnx_path)
            
            # Benchmark performance
            benchmark_results = self.benchmark_model(engine_path, onnx_path)
            
            # Log to MLflow
            run_id = self.log_to_mlflow(engine_path, onnx_path, benchmark_results)
            
            logger.info("🎉 TensorRT conversion completed successfully!")
            logger.info(f"Optimized model: {engine_path}")
            logger.info(f"MLflow run: {run_id}")
            
            return run_id
            
        except Exception as e:
            logger.error(f"💥 Conversion failed: {e}")
            raise

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='TensorRT Model Optimization Pipeline')
    
    # Model source (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--model-uri', type=str,
                             help='Direct MLflow model URI (e.g., runs:/abc123/model)')
    source_group.add_argument('--run-id', type=str,
                             help='MLflow run ID containing the model')
    source_group.add_argument('--model-name', type=str,
                             help='Registered model name in MLflow Model Registry')
    
    parser.add_argument('--version', type=str,
                       help='Model version (only with --model-name)')
    
    # TensorRT optimization settings
    parser.add_argument('--precision', type=str, default='fp16',
                       choices=['fp32', 'fp16', 'int8'],
                       help='TensorRT precision mode')
    
    parser.add_argument('--max-batch-size', type=int, default=8,
                       help='Maximum batch size for optimization')
    
    parser.add_argument('--max-workspace-size', type=float, default=1.0,
                       help='Maximum workspace size in GB')
    
    parser.add_argument('--force-rebuild', action='store_true',
                       help='Force rebuild even if engine exists')
    
    return parser.parse_args()

def main():
    """Main conversion entry point"""
    args = parse_arguments()
    
    logger.info("🔧 TensorRT Model Optimization for Edge Deployment")
    logger.info(f"Precision: {args.precision}")
    logger.info(f"Max Batch Size: {args.max_batch_size}")
    logger.info(f"Max Workspace: {args.max_workspace_size}GB")
    
    try:
        converter = TensorRTConverter(args)
        run_id = converter.convert()
        
        logger.info(f"🚀 Ready for edge deployment!")
        logger.info(f"View results at: {os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")
        
    except Exception as e:
        logger.error(f"💥 Optimization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
