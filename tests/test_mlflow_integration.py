#!/usr/bin/env python3
"""
Comprehensive MLflow Integration Tests

This test suite validates:
1. MLflow server connectivity and configuration
2. Model training pipeline with proper logging
3. Model registry operations and versioning
4. Artifact storage and retrieval
5. TensorRT optimization workflow
6. Deployment readiness validation

Usage:
    pytest tests/test_mlflow_integration.py -v
    pytest tests/test_mlflow_integration.py::TestMLflowServer -v
    pytest tests/test_mlflow_integration.py::TestModelTraining -v

Environment Variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URI
    TEST_DATASET_PATH: Path to test dataset
"""

import os
import sys
import json
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# MLflow imports
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient
from mlflow.entities import Experiment, Run, ModelVersion
from mlflow.exceptions import MlflowException

# Import our modules
from infra.mlflow_server import MLflowServer, ServerConfig
from train.train import ModelTrainer, SurveillanceDataset
from train.convert_to_trt import TensorRTConverter

class TestMLflowServer:
    """Test MLflow server setup and configuration"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def server_config(self, temp_dir):
        """Create test server configuration"""
        return ServerConfig(
            backend_store_uri=f"sqlite:///{temp_dir}/mlflow.db",
            default_artifact_root=f"file://{temp_dir}/artifacts",
            host="127.0.0.1",
            port=5555,  # Use different port for testing
            workers=1
        )
    
    def test_server_config_creation(self, server_config):
        """Test server configuration creation"""
        assert server_config.backend_store_uri.startswith("sqlite:///")
        assert server_config.default_artifact_root.startswith("file://")
        assert server_config.host == "127.0.0.1"
        assert server_config.port == 5555
        assert server_config.workers == 1
    
    def test_server_initialization(self, server_config):
        """Test MLflow server initialization"""
        server = MLflowServer(server_config)
        
        assert server.config == server_config
        assert server.process is None
        assert not server.is_running()
    
    def test_server_validation(self, server_config, temp_dir):
        """Test server configuration validation"""
        server = MLflowServer(server_config)
        
        # Create required directories
        artifacts_dir = Path(temp_dir) / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        # Should not raise any exceptions
        server._validate_config()
    
    def test_database_initialization(self, server_config, temp_dir):
        """Test database initialization"""
        server = MLflowServer(server_config)
        server._init_database()
        
        # Check if database file was created
        db_path = Path(temp_dir) / "mlflow.db"
        assert db_path.exists()
    
    @pytest.mark.integration
    def test_server_lifecycle(self, server_config, temp_dir):
        """Test complete server lifecycle"""
        server = MLflowServer(server_config)
        
        try:
            # Start server
            server.start()
            assert server.is_running()
            
            # Wait for server to be ready
            time.sleep(5)
            
            # Test health check
            health_status = server.health_check()
            assert health_status["status"] == "healthy"
            
            # Test MLflow client connection
            mlflow.set_tracking_uri(f"http://127.0.0.1:5555")
            
            # Create test experiment
            experiment_id = mlflow.create_experiment("test_experiment")
            assert experiment_id is not None
            
        finally:
            # Stop server
            server.stop()
            assert not server.is_running()

class TestMLflowTracking:
    """Test MLflow experiment tracking and logging"""
    
    @pytest.fixture
    def mlflow_client(self):
        """Setup MLflow client for testing"""
        # Use ephemeral tracking URI for testing
        tracking_uri = "sqlite:///memory"
        mlflow.set_tracking_uri(tracking_uri)
        
        client = MlflowClient()
        yield client
        
        # Cleanup
        mlflow.end_run()
    
    @pytest.fixture
    def test_experiment(self, mlflow_client):
        """Create test experiment"""
        experiment_name = "test_surveillance_models"
        
        try:
            experiment_id = mlflow.create_experiment(experiment_name)
        except MlflowException:
            # Experiment might already exist
            experiment = mlflow.get_experiment_by_name(experiment_name)
            experiment_id = experiment.experiment_id
        
        mlflow.set_experiment(experiment_name)
        return experiment_id
    
    def test_experiment_creation(self, mlflow_client, test_experiment):
        """Test experiment creation and retrieval"""
        experiment = mlflow_client.get_experiment(test_experiment)
        
        assert experiment.name == "test_surveillance_models"
        assert experiment.lifecycle_stage == "active"
    
    def test_run_logging(self, test_experiment):
        """Test basic run logging functionality"""
        with mlflow.start_run() as run:
            # Log parameters
            mlflow.log_param("model_type", "mobilenet_v3")
            mlflow.log_param("epochs", 10)
            mlflow.log_param("batch_size", 32)
            
            # Log metrics
            for epoch in range(5):
                mlflow.log_metric("train_loss", 1.0 - (epoch * 0.1), step=epoch)
                mlflow.log_metric("val_accuracy", 60.0 + (epoch * 5), step=epoch)
            
            # Log tags
            mlflow.set_tag("environment", "test")
            mlflow.set_tag("model_purpose", "surveillance")
            
            run_id = run.info.run_id
        
        # Verify logged data
        client = MlflowClient()
        run_data = client.get_run(run_id)
        
        assert run_data.data.params["model_type"] == "mobilenet_v3"
        assert run_data.data.params["epochs"] == "10"
        assert run_data.data.tags["environment"] == "test"
        
        # Check metrics
        train_loss_history = client.get_metric_history(run_id, "train_loss")
        val_acc_history = client.get_metric_history(run_id, "val_accuracy")
        
        assert len(train_loss_history) == 5
        assert len(val_acc_history) == 5
        assert train_loss_history[-1].value == 0.6  # 1.0 - (4 * 0.1)
        assert val_acc_history[-1].value == 80.0   # 60.0 + (4 * 5)
    
    def test_artifact_logging(self, test_experiment):
        """Test artifact logging and retrieval"""
        with mlflow.start_run() as run:
            # Create test artifacts
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a test model file
                model_path = Path(temp_dir) / "test_model.pt"
                torch.save({"state_dict": {}, "epoch": 10}, model_path)
                
                # Create a test config file
                config_path = Path(temp_dir) / "config.json"
                config = {"lr": 0.001, "batch_size": 32}
                with open(config_path, 'w') as f:
                    json.dump(config, f)
                
                # Log artifacts
                mlflow.log_artifact(str(model_path), "models")
                mlflow.log_artifact(str(config_path), "configs")
                
                run_id = run.info.run_id
        
        # Verify artifacts were logged
        client = MlflowClient()
        artifacts = client.list_artifacts(run_id)
        
        artifact_paths = [a.path for a in artifacts]
        assert "models" in artifact_paths
        assert "configs" in artifact_paths
        
        # Download and verify artifacts
        with tempfile.TemporaryDirectory() as download_dir:
            downloaded_path = mlflow.artifacts.download_artifacts(
                run_id=run_id,
                artifact_path="models/test_model.pt",
                dst_path=download_dir
            )
            
            assert os.path.exists(downloaded_path)
            
            # Verify model can be loaded
            loaded_model = torch.load(downloaded_path)
            assert loaded_model["epoch"] == 10

class TestModelTraining:
    """Test model training pipeline with MLflow integration"""
    
    @pytest.fixture
    def mock_args(self):
        """Create mock training arguments"""
        args = Mock()
        args.model = "mobilenet_v3"
        args.epochs = 2  # Short for testing
        args.batch_size = 4
        args.lr = 0.001
        args.img_size = 32  # Small for testing
        args.seed = 42
        return args
    
    @pytest.fixture
    def sample_dataset(self):
        """Create sample dataset for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir)
            
            # Create class directories
            for split in ['train', 'val']:
                for class_name in ['person', 'vehicle']:
                    class_dir = dataset_path / split / class_name
                    class_dir.mkdir(parents=True)
                    
                    # Create sample images
                    for i in range(3):
                        img = Image.fromarray(np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8))
                        img.save(class_dir / f"sample_{i}.jpg")
            
            yield str(dataset_path)
    
    def test_dataset_loading(self, sample_dataset):
        """Test surveillance dataset loading"""
        from albumentations.pytorch import ToTensorV2
        import albumentations as A
        
        transform = A.Compose([
            A.Resize(32, 32),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
        
        train_dataset = SurveillanceDataset(
            data_path=f"{sample_dataset}/train",
            transform=transform
        )
        
        assert len(train_dataset) == 6  # 2 classes * 3 images
        assert len(train_dataset.classes) == 10  # All surveillance classes
        
        # Test data loading
        image, label = train_dataset[0]
        assert isinstance(image, torch.Tensor)
        assert image.shape == (3, 32, 32)
        assert isinstance(label, int)
        assert 0 <= label < len(train_dataset.classes)
    
    @patch.dict(os.environ, {
        'MLFLOW_TRACKING_URI': 'sqlite:///memory',
        'DATASET_PATH': ''
    })
    def test_trainer_initialization(self, mock_args, sample_dataset):
        """Test model trainer initialization"""
        # Set dataset path in environment
        os.environ['DATASET_PATH'] = sample_dataset
        
        trainer = ModelTrainer(mock_args)
        
        assert trainer.args == mock_args
        assert trainer.device in [torch.device('cpu'), torch.device('cuda')]
        assert trainer.train_transform is not None
        assert trainer.val_transform is not None
    
    @patch.dict(os.environ, {
        'MLFLOW_TRACKING_URI': 'sqlite:///memory',
        'DATASET_PATH': ''
    })
    def test_model_creation(self, mock_args, sample_dataset):
        """Test model creation for different architectures"""
        os.environ['DATASET_PATH'] = sample_dataset
        trainer = ModelTrainer(mock_args)
        
        # Test MobileNet creation
        mock_args.model = "mobilenet_v3"
        model = trainer._create_model()
        assert isinstance(model, nn.Module)
        
        # Test EfficientNet creation
        mock_args.model = "efficientnet_b0"
        model = trainer._create_model()
        assert isinstance(model, nn.Module)
        
        # Test invalid model
        mock_args.model = "invalid_model"
        with pytest.raises(ValueError):
            trainer._create_model()
    
    @patch.dict(os.environ, {
        'MLFLOW_TRACKING_URI': 'sqlite:///memory',
        'DATASET_PATH': ''
    })
    @patch('train.train.mlflow')
    def test_training_with_mlflow_logging(self, mock_mlflow, mock_args, sample_dataset):
        """Test training pipeline with MLflow logging"""
        os.environ['DATASET_PATH'] = sample_dataset
        
        # Mock MLflow run context
        mock_run = Mock()
        mock_run.info.run_id = "test_run_id"
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
        mock_mlflow.active_run.return_value = mock_run
        
        trainer = ModelTrainer(mock_args)
        
        # Mock model creation to use a simple model for testing
        def create_simple_model():
            return nn.Sequential(
                nn.Conv2d(3, 16, 3, padding=1),
                nn.AdaptiveAvgPool2d((1, 1)),
                nn.Flatten(),
                nn.Linear(16, 10)  # 10 classes
            )
        
        trainer._create_model = create_simple_model
        
        # Run training
        run_id = trainer.train()
        
        # Verify MLflow calls
        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.log_params.assert_called()
        mock_mlflow.log_metrics.assert_called()
        
        assert run_id == "test_run_id"

class TestModelRegistry:
    """Test MLflow Model Registry operations"""
    
    @pytest.fixture
    def registry_client(self):
        """Setup MLflow client for model registry testing"""
        mlflow.set_tracking_uri("sqlite:///memory")
        client = MlflowClient()
        yield client
    
    def test_model_registration(self, registry_client):
        """Test model registration in MLflow Model Registry"""
        model_name = "test_surveillance_model"
        
        # Create a simple model and log it
        with mlflow.start_run() as run:
            model = nn.Linear(10, 2)
            mlflow.pytorch.log_model(
                model,
                "pytorch_model",
                registered_model_name=model_name
            )
            run_id = run.info.run_id
        
        # Verify model was registered
        registered_models = registry_client.search_registered_models(
            filter_string=f"name='{model_name}'"
        )
        
        assert len(registered_models) == 1
        assert registered_models[0].name == model_name
        
        # Check model version
        model_versions = registry_client.search_model_versions(
            filter_string=f"name='{model_name}'"
        )
        
        assert len(model_versions) == 1
        assert model_versions[0].current_stage == "None"
    
    def test_model_stage_transitions(self, registry_client):
        """Test model stage transitions in registry"""
        model_name = "test_model_transitions"
        
        # Register a model
        with mlflow.start_run() as run:
            model = nn.Linear(5, 3)
            model_version = mlflow.register_model(
                f"runs:/{run.info.run_id}/pytorch_model",
                model_name
            )
        
        # Transition to Staging
        registry_client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Staging"
        )
        
        # Verify stage transition
        model_version = registry_client.get_model_version(
            name=model_name,
            version=model_version.version
        )
        assert model_version.current_stage == "Staging"
        
        # Transition to Production
        registry_client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Production"
        )
        
        # Verify production stage
        model_version = registry_client.get_model_version(
            name=model_name,
            version=model_version.version
        )
        assert model_version.current_stage == "Production"
    
    def test_model_versioning(self, registry_client):
        """Test model versioning capabilities"""
        model_name = "test_model_versioning"
        
        # Register multiple versions
        for i in range(3):
            with mlflow.start_run() as run:
                model = nn.Linear(10, 2)
                mlflow.pytorch.log_model(
                    model,
                    "pytorch_model",
                    registered_model_name=model_name
                )
        
        # Check all versions exist
        model_versions = registry_client.search_model_versions(
            filter_string=f"name='{model_name}'"
        )
        
        assert len(model_versions) == 3
        
        # Check version numbers
        version_numbers = [int(mv.version) for mv in model_versions]
        assert sorted(version_numbers) == [1, 2, 3]
        
        # Test getting latest version
        latest_versions = registry_client.get_latest_versions(
            model_name,
            stages=["None"]
        )
        
        assert len(latest_versions) == 1
        assert int(latest_versions[0].version) == 3

class TestTensorRTIntegration:
    """Test TensorRT conversion and optimization"""
    
    @pytest.fixture
    def mock_trt_args(self):
        """Create mock TensorRT arguments"""
        args = Mock()
        args.model_name = "test_model"
        args.version = "1"
        args.model_uri = None
        args.run_id = None
        args.precision = "fp16"
        args.max_batch_size = 4
        args.max_workspace_size = 1.0
        args.force_rebuild = False
        return args
    
    @pytest.fixture
    def sample_onnx_model(self):
        """Create sample ONNX model for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            onnx_path = Path(temp_dir) / "test_model.onnx"
            
            # Create a simple PyTorch model
            model = nn.Sequential(
                nn.Conv2d(3, 16, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, 1)),
                nn.Flatten(),
                nn.Linear(16, 10)
            )
            
            # Export to ONNX
            dummy_input = torch.randn(1, 3, 32, 32)
            torch.onnx.export(
                model,
                dummy_input,
                str(onnx_path),
                export_params=True,
                opset_version=11,
                input_names=['input'],
                output_names=['output']
            )
            
            yield str(onnx_path)
    
    @patch('train.convert_to_trt.trt')
    @patch('train.convert_to_trt.GPUtil')
    def test_converter_initialization(self, mock_gputil, mock_trt, mock_trt_args):
        """Test TensorRT converter initialization"""
        # Mock GPU detection
        mock_gpu = Mock()
        mock_gpu.name = "Test GPU"
        mock_gpu.memoryTotal = 8192
        mock_gpu.memoryFree = 6144
        mock_gputil.getGPUs.return_value = [mock_gpu]
        
        # Mock TensorRT version
        mock_trt.__version__ = "8.0.0"
        
        converter = TensorRTConverter(mock_trt_args)
        
        assert converter.args == mock_trt_args
        assert converter.client is not None
        assert converter.cache_dir.exists()
    
    @patch('train.convert_to_trt.mlflow')
    def test_model_download(self, mock_mlflow, mock_trt_args, sample_onnx_model):
        """Test model download from MLflow"""
        # Mock MLflow artifacts download
        mock_mlflow.artifacts.download_artifacts.return_value = str(Path(sample_onnx_model).parent)
        
        converter = TensorRTConverter(mock_trt_args)
        
        # Test download with model name and version
        downloaded_path = converter.download_model()
        
        assert downloaded_path is not None
        mock_mlflow.artifacts.download_artifacts.assert_called_once()
    
    @patch('train.convert_to_trt.trt')
    def test_engine_building_mock(self, mock_trt, mock_trt_args, sample_onnx_model):
        """Test TensorRT engine building (mocked)"""
        # Mock TensorRT components
        mock_builder = Mock()
        mock_config = Mock()
        mock_network = Mock()
        mock_parser = Mock()
        mock_engine = b"fake_engine_data"
        
        mock_trt.Builder.return_value = mock_builder
        mock_builder.create_builder_config.return_value = mock_config
        mock_builder.create_network.return_value = mock_network
        mock_trt.OnnxParser.return_value = mock_parser
        mock_parser.parse.return_value = True
        mock_parser.num_errors = 0
        mock_builder.build_serialized_network.return_value = mock_engine
        
        # Mock input tensor
        mock_input_tensor = Mock()
        mock_input_tensor.name = "input"
        mock_input_tensor.shape = [1, 3, 32, 32]
        mock_network.get_input.return_value = mock_input_tensor
        
        converter = TensorRTConverter(mock_trt_args)
        
        # Build engine
        engine_path = converter.build_trt_engine(sample_onnx_model)
        
        assert engine_path.endswith(".engine")
        mock_trt.Builder.assert_called_once()
        mock_builder.create_builder_config.assert_called_once()
    
    @patch('train.convert_to_trt.mlflow')
    def test_mlflow_logging(self, mock_mlflow, mock_trt_args):
        """Test MLflow logging for TensorRT optimization"""
        # Mock MLflow run
        mock_run = Mock()
        mock_run.info.run_id = "optimization_run_id"
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
        
        converter = TensorRTConverter(mock_trt_args)
        
        # Mock benchmark results
        benchmark_results = {
            'tensorrt_latency_ms': 5.0,
            'onnx_latency_ms': 10.0,
            'latency_improvement_percent': 50.0,
            'tensorrt_throughput_fps': 200.0,
            'onnx_throughput_fps': 100.0,
            'throughput_improvement_percent': 100.0,
            'tensorrt_model_size_mb': 5.0,
            'onnx_model_size_mb': 10.0,
            'precision': 'fp16',
            'max_batch_size': 4,
            'benchmark_iterations': 100
        }
        
        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            engine_path = Path(temp_dir) / "test.engine"
            onnx_path = Path(temp_dir) / "test.onnx"
            
            # Create dummy files
            engine_path.write_bytes(b"fake_engine")
            onnx_path.write_bytes(b"fake_onnx")
            
            run_id = converter.log_to_mlflow(str(engine_path), str(onnx_path), benchmark_results)
            
            assert run_id == "optimization_run_id"
            mock_mlflow.start_run.assert_called_once()
            mock_mlflow.log_params.assert_called_once()
            mock_mlflow.log_metrics.assert_called_once_with(benchmark_results)

class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""
    
    @pytest.fixture
    def workflow_setup(self):
        """Setup for end-to-end workflow testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup MLflow tracking
            mlflow.set_tracking_uri("sqlite:///memory")
            
            # Create sample dataset
            dataset_path = Path(temp_dir) / "dataset"
            for split in ['train', 'val']:
                for class_name in ['person', 'vehicle']:
                    class_dir = dataset_path / split / class_name
                    class_dir.mkdir(parents=True)
                    
                    # Create minimal sample images
                    for i in range(2):
                        img = Image.fromarray(np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8))
                        img.save(class_dir / f"sample_{i}.jpg")
            
            yield {
                'temp_dir': temp_dir,
                'dataset_path': str(dataset_path)
            }
    
    @patch.dict(os.environ, {
        'MLFLOW_TRACKING_URI': 'sqlite:///memory',
        'DATASET_PATH': ''
    })
    @patch('train.train.mlflow')
    def test_complete_training_workflow(self, mock_mlflow, workflow_setup):
        """Test complete training workflow with MLflow integration"""
        os.environ['DATASET_PATH'] = workflow_setup['dataset_path']
        
        # Mock MLflow components
        mock_run = Mock()
        mock_run.info.run_id = "workflow_test_run"
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run
        mock_mlflow.active_run.return_value = mock_run
        
        # Create mock training arguments
        args = Mock()
        args.model = "mobilenet_v3"
        args.epochs = 1  # Minimal for testing
        args.batch_size = 2
        args.lr = 0.001
        args.img_size = 32
        args.seed = 42
        
        trainer = ModelTrainer(args)
        
        # Mock model creation for faster testing
        def create_test_model():
            return nn.Sequential(
                nn.Conv2d(3, 8, 3, padding=1),
                nn.AdaptiveAvgPool2d((1, 1)),
                nn.Flatten(),
                nn.Linear(8, 10)
            )
        
        trainer._create_model = create_test_model
        
        # Run training
        run_id = trainer.train()
        
        # Verify workflow completed
        assert run_id == "workflow_test_run"
        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.log_params.assert_called()
        mock_mlflow.log_metrics.assert_called()
    
    def test_model_registry_workflow(self, workflow_setup):
        """Test model registry workflow"""
        client = MlflowClient()
        model_name = "test_workflow_model"
        
        # Step 1: Train and register model
        with mlflow.start_run() as run:
            model = nn.Linear(10, 2)
            mlflow.pytorch.log_model(
                model,
                "pytorch_model",
                registered_model_name=model_name
            )
            run_id = run.info.run_id
        
        # Step 2: Transition to Staging
        model_versions = client.search_model_versions(f"name='{model_name}'")
        version = model_versions[0].version
        
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Staging"
        )
        
        # Step 3: Validate staging deployment
        staging_models = client.get_latest_versions(model_name, stages=["Staging"])
        assert len(staging_models) == 1
        assert staging_models[0].current_stage == "Staging"
        
        # Step 4: Transition to Production
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )
        
        # Step 5: Validate production deployment
        production_models = client.get_latest_versions(model_name, stages=["Production"])
        assert len(production_models) == 1
        assert production_models[0].current_stage == "Production"

# Performance and load testing
class TestPerformance:
    """Test performance and scalability"""
    
    def test_concurrent_runs(self):
        """Test handling concurrent MLflow runs"""
        mlflow.set_tracking_uri("sqlite:///memory")
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_run(run_name):
            try:
                with mlflow.start_run(run_name=run_name):
                    mlflow.log_param("test_param", run_name)
                    mlflow.log_metric("test_metric", np.random.random())
                    results.put(("success", run_name))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Create multiple concurrent runs
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_run, args=(f"concurrent_run_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, message = results.get()
            if status == "success":
                success_count += 1
            else:
                error_count += 1
                print(f"Error: {message}")
        
        assert success_count == 5
        assert error_count == 0
    
    def test_large_artifact_handling(self):
        """Test handling of large artifacts"""
        mlflow.set_tracking_uri("sqlite:///memory")
        
        with mlflow.start_run():
            # Create a moderately large artifact (1MB)
            with tempfile.NamedTemporaryFile(delete=False) as f:
                large_data = np.random.bytes(1024 * 1024)  # 1MB
                f.write(large_data)
                f.flush()
                
                # Log artifact
                mlflow.log_artifact(f.name, "large_artifacts")
                
                # Cleanup
                os.unlink(f.name)
        
        # Verify artifact was logged successfully
        client = MlflowClient()
        runs = mlflow.search_runs()
        assert len(runs) == 1
        
        run_id = runs.iloc[0]['run_id']
        artifacts = client.list_artifacts(run_id, "large_artifacts")
        assert len(artifacts) == 1

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
