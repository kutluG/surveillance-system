#!/usr/bin/env python3
"""
MLflow Training Pipeline for Edge Inference Models

This script trains models for surveillance system edge inference with comprehensive MLflow tracking:
1. Logs hyperparameters, metrics, and artifacts
2. Converts models to ONNX format for edge deployment
3. Registers models in MLflow Model Registry
4. Supports multiple model architectures (YOLO, MobileNet, EfficientNet)

Usage:
    python train/train.py --model yolov8n --epochs 50 --batch-size 32
    python train/train.py --model mobilenet_v3 --epochs 100 --lr 0.001

Environment Variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URI
    MLFLOW_EXPERIMENT_NAME: Experiment name for grouping runs
    DATASET_PATH: Path to training dataset
    MODEL_REGISTRY_STAGE: Target stage for model registration (Staging/Production)
"""

import os
import sys
import json
import argparse
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# MLflow imports
try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    from mlflow.models.signature import infer_signature
    from mlflow.tracking import MlflowClient
except ImportError:
    print("ERROR: MLflow not installed. Run: pip install mlflow")
    sys.exit(1)

# PyTorch imports
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    import torchvision
    import torchvision.transforms as transforms
    from torchvision.models import mobilenet_v3_small, efficientnet_b0
    import onnx
    import onnxruntime as ort
except ImportError as e:
    print(f"ERROR: PyTorch/ONNX dependencies missing: {e}")
    print("Install with: pip install torch torchvision onnx onnxruntime")
    sys.exit(1)

# Additional dependencies
try:
    import numpy as np
    import cv2
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    import yaml
    from ultralytics import YOLO
except ImportError as e:
    print(f"ERROR: Additional dependencies missing: {e}")
    print("Install with: pip install numpy opencv-python scikit-learn albumentations ultralytics pyyaml")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mlflow_training')

class SurveillanceDataset(Dataset):
    """Custom dataset for surveillance object detection/classification"""
    
    def __init__(self, data_path: str, transform=None, mode: str = 'classification'):
        self.data_path = Path(data_path)
        self.transform = transform
        self.mode = mode
        self.samples = self._load_samples()
        
        # Class mapping for surveillance objects
        self.classes = [
            'person', 'vehicle', 'bike', 'animal', 'package', 
            'weapon', 'fire', 'smoke', 'crowd', 'vandalism'
        ]
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}
        
    def _load_samples(self) -> List[Dict]:
        """Load dataset samples from directory structure or annotations file"""
        samples = []
        
        # Check for YOLO format annotations
        if (self.data_path / "data.yaml").exists():
            with open(self.data_path / "data.yaml", 'r') as f:
                config = yaml.safe_load(f)
            
            train_path = self.data_path / config.get('train', 'train')
            if train_path.exists():
                for img_file in train_path.glob("*.jpg"):
                    label_file = img_file.with_suffix('.txt')
                    if label_file.exists():
                        samples.append({
                            'image_path': str(img_file),
                            'label_path': str(label_file),
                            'type': 'detection'
                        })
        
        # Classification format: class folders
        elif any(p.is_dir() for p in self.data_path.iterdir()):
            for class_dir in self.data_path.iterdir():
                if class_dir.is_dir() and class_dir.name in self.classes:
                    for img_file in class_dir.glob("*.jpg"):
                        samples.append({
                            'image_path': str(img_file),
                            'label': self.class_to_idx[class_dir.name],
                            'type': 'classification'
                        })
        
        logger.info(f"Loaded {len(samples)} samples from {self.data_path}")
        return samples
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Any]:
        sample = self.samples[idx]
        
        # Load image
        image = cv2.imread(sample['image_path'])
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if sample['type'] == 'classification':
            label = sample['label']
            
            if self.transform:
                transformed = self.transform(image=image)
                image = transformed['image']
            
            return image, label
        
        elif sample['type'] == 'detection':
            # For detection, return image and bounding boxes
            boxes = []
            if Path(sample['label_path']).exists():
                with open(sample['label_path'], 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cls, x, y, w, h = map(float, parts[:5])
                            boxes.append([cls, x, y, w, h])
            
            if self.transform:
                transformed = self.transform(image=image, bboxes=boxes)
                image = transformed['image']
                boxes = transformed.get('bboxes', boxes)
            
            return image, torch.tensor(boxes, dtype=torch.float32)

class ModelTrainer:
    """MLflow-integrated model trainer for surveillance edge models"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize MLflow
        self._setup_mlflow()
        
        # Setup data transforms
        self.train_transform = A.Compose([
            A.Resize(args.img_size, args.img_size),
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(p=0.3),
            A.Blur(blur_limit=3, p=0.2),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.2),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
        
        self.val_transform = A.Compose([
            A.Resize(args.img_size, args.img_size),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
    
    def _setup_mlflow(self):
        """Setup MLflow tracking and experiment"""
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        
        experiment_name = os.getenv('MLFLOW_EXPERIMENT_NAME', 'surveillance-edge-models')
        
        try:
            experiment_id = mlflow.create_experiment(experiment_name)
        except Exception:
            experiment_id = mlflow.get_experiment_by_name(experiment_name).experiment_id
        
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow tracking URI: {mlflow_uri}")
        logger.info(f"Experiment: {experiment_name} (ID: {experiment_id})")
    
    def _create_model(self) -> nn.Module:
        """Create model based on architecture selection"""
        if self.args.model == 'yolov8n':
            # Use Ultralytics YOLO for detection
            model = YOLO('yolov8n.pt')
            return model
        
        elif self.args.model == 'mobilenet_v3':
            model = mobilenet_v3_small(pretrained=True)
            # Modify classifier for surveillance classes
            model.classifier[3] = nn.Linear(model.classifier[3].in_features, 10)
            return model
        
        elif self.args.model == 'efficientnet_b0':
            model = efficientnet_b0(pretrained=True)
            # Modify classifier for surveillance classes
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, 10)
            return model
        
        else:
            raise ValueError(f"Unsupported model architecture: {self.args.model}")
    
    def _create_dataloaders(self) -> Tuple[DataLoader, DataLoader]:
        """Create train and validation data loaders"""
        dataset_path = os.getenv('DATASET_PATH', 'data/surveillance_dataset')
        
        train_dataset = SurveillanceDataset(
            data_path=f"{dataset_path}/train",
            transform=self.train_transform
        )
        
        val_dataset = SurveillanceDataset(
            data_path=f"{dataset_path}/val",
            transform=self.val_transform
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.args.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.args.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )
        
        return train_loader, val_loader
    
    def _train_epoch(self, model: nn.Module, train_loader: DataLoader, 
                    optimizer: optim.Optimizer, criterion: nn.Module) -> Dict[str, float]:
        """Train model for one epoch"""
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = output.max(1)
            total += target.size(0)
            correct += predicted.eq(target).sum().item()
            
            if batch_idx % 50 == 0:
                logger.info(f'Batch {batch_idx}/{len(train_loader)}, Loss: {loss.item():.4f}')
        
        epoch_loss = total_loss / len(train_loader)
        epoch_acc = 100. * correct / total
        
        return {'loss': epoch_loss, 'accuracy': epoch_acc}
    
    def _validate_epoch(self, model: nn.Module, val_loader: DataLoader, 
                       criterion: nn.Module) -> Dict[str, float]:
        """Validate model for one epoch"""
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                
                output = model(data)
                loss = criterion(output, target)
                
                total_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()
                
                all_preds.extend(predicted.cpu().numpy())
                all_targets.extend(target.cpu().numpy())
        
        epoch_loss = total_loss / len(val_loader)
        epoch_acc = 100. * correct / total
        
        # Calculate additional metrics
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_targets, all_preds, average='weighted', zero_division=0
        )
        
        return {
            'loss': epoch_loss,
            'accuracy': epoch_acc,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }
    
    def _convert_to_onnx(self, model: nn.Module, model_path: str) -> str:
        """Convert PyTorch model to ONNX format"""
        model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(1, 3, self.args.img_size, self.args.img_size).to(self.device)
        
        # Export to ONNX
        onnx_path = model_path.replace('.pt', '.onnx')
        
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        
        # Verify ONNX model
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        
        # Test ONNX Runtime inference
        ort_session = ort.InferenceSession(onnx_path)
        
        # Convert dummy input to numpy
        dummy_input_np = dummy_input.cpu().numpy()
        ort_inputs = {ort_session.get_inputs()[0].name: dummy_input_np}
        ort_outputs = ort_session.run(None, ort_inputs)
        
        logger.info(f"✅ ONNX model created and verified: {onnx_path}")
        return onnx_path
    
    def train(self) -> str:
        """Main training loop with MLflow tracking"""
        
        with mlflow.start_run(run_name=f"{self.args.model}_edge_training") as run:
            run_id = run.info.run_id
            logger.info(f"Started MLflow run: {run_id}")
            
            # Log parameters
            mlflow.log_params({
                'model_architecture': self.args.model,
                'epochs': self.args.epochs,
                'batch_size': self.args.batch_size,
                'learning_rate': self.args.lr,
                'img_size': self.args.img_size,
                'optimizer': 'Adam',
                'device': str(self.device),
                'pytorch_version': torch.__version__,
                'training_timestamp': datetime.now().isoformat()
            })
            
            # Create model and data loaders
            if self.args.model == 'yolov8n':
                # Handle YOLO training separately
                return self._train_yolo()
            
            model = self._create_model().to(self.device)
            train_loader, val_loader = self._create_dataloaders()
            
            # Setup training components
            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(model.parameters(), lr=self.args.lr)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)
            
            # Log model summary
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            mlflow.log_params({
                'total_parameters': total_params,
                'trainable_parameters': trainable_params,
                'model_size_mb': total_params * 4 / (1024 * 1024)  # Approximate size in MB
            })
            
            # Training loop
            best_val_acc = 0.0
            best_model_path = None
            
            for epoch in range(self.args.epochs):
                logger.info(f"Epoch {epoch+1}/{self.args.epochs}")
                
                # Train
                train_metrics = self._train_epoch(model, train_loader, optimizer, criterion)
                
                # Validate
                val_metrics = self._validate_epoch(model, val_loader, criterion)
                
                # Update learning rate
                scheduler.step(val_metrics['loss'])
                current_lr = optimizer.param_groups[0]['lr']
                
                # Log metrics
                mlflow.log_metrics({
                    'train_loss': train_metrics['loss'],
                    'train_accuracy': train_metrics['accuracy'],
                    'val_loss': val_metrics['loss'],
                    'val_accuracy': val_metrics['accuracy'],
                    'val_precision': val_metrics['precision'],
                    'val_recall': val_metrics['recall'],
                    'val_f1_score': val_metrics['f1_score'],
                    'learning_rate': current_lr
                }, step=epoch)
                
                logger.info(f"Train Loss: {train_metrics['loss']:.4f}, "
                          f"Train Acc: {train_metrics['accuracy']:.2f}%")
                logger.info(f"Val Loss: {val_metrics['loss']:.4f}, "
                          f"Val Acc: {val_metrics['accuracy']:.2f}%")
                
                # Save best model
                if val_metrics['accuracy'] > best_val_acc:
                    best_val_acc = val_metrics['accuracy']
                    best_model_path = f"best_model_{self.args.model}_epoch_{epoch+1}.pt"
                    torch.save({
                        'epoch': epoch,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'val_accuracy': val_metrics['accuracy'],
                        'train_args': vars(self.args)
                    }, best_model_path)
                    
                    logger.info(f"✅ New best model saved: {best_model_path}")
            
            # Final model artifacts
            if best_model_path:
                # Convert to ONNX
                model.load_state_dict(torch.load(best_model_path)['model_state_dict'])
                onnx_path = self._convert_to_onnx(model, best_model_path)
                
                # Log model artifacts
                mlflow.log_artifact(best_model_path, "models")
                mlflow.log_artifact(onnx_path, "models")
                
                # Create model signature for MLflow model logging
                sample_input = torch.randn(1, 3, self.args.img_size, self.args.img_size)
                model.eval()
                with torch.no_grad():
                    sample_output = model(sample_input)
                
                signature = infer_signature(sample_input.numpy(), sample_output.numpy())
                
                # Log model to MLflow
                mlflow.pytorch.log_model(
                    model,
                    "pytorch_model",
                    signature=signature,
                    input_example=sample_input.numpy(),
                    registered_model_name=f"surveillance_{self.args.model}_edge"
                )
                
                # Register model in Model Registry
                self._register_model(f"surveillance_{self.args.model}_edge", run_id)
                
                logger.info(f"✅ Model training completed successfully!")
                logger.info(f"Best validation accuracy: {best_val_acc:.2f}%")
                
                return run_id
            
            else:
                raise Exception("No model was saved during training")
    
    def _train_yolo(self) -> str:
        """Train YOLO model with MLflow tracking"""
        dataset_path = os.getenv('DATASET_PATH', 'data/surveillance_dataset')
        
        # YOLO training configuration
        yolo_config = {
            'data': f"{dataset_path}/data.yaml",
            'epochs': self.args.epochs,
            'imgsz': self.args.img_size,
            'batch': self.args.batch_size,
            'lr0': self.args.lr,
            'project': 'runs/detect',
            'name': f'yolo_edge_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'save': True,
            'save_period': 10
        }
        
        # Log YOLO-specific parameters
        mlflow.log_params(yolo_config)
        
        # Initialize YOLO model
        model = YOLO('yolov8n.pt')
        
        # Train with custom callback for MLflow logging
        def on_train_epoch_end(trainer):
            if hasattr(trainer, 'epoch') and hasattr(trainer, 'loss_items'):
                epoch = trainer.epoch
                losses = trainer.loss_items
                
                mlflow.log_metrics({
                    'yolo_box_loss': losses.get('train/box_loss', 0),
                    'yolo_cls_loss': losses.get('train/cls_loss', 0),
                    'yolo_dfl_loss': losses.get('train/dfl_loss', 0),
                }, step=epoch)
        
        # Start training
        results = model.train(**yolo_config)
        
        # Log final metrics
        if hasattr(results, 'results_dict'):
            final_metrics = results.results_dict
            mlflow.log_metrics({
                'final_map50': final_metrics.get('metrics/mAP50(B)', 0),
                'final_map50_95': final_metrics.get('metrics/mAP50-95(B)', 0),
                'final_precision': final_metrics.get('metrics/precision(B)', 0),
                'final_recall': final_metrics.get('metrics/recall(B)', 0)
            })
        
        # Save and log model artifacts
        best_model_path = f"{yolo_config['project']}/{yolo_config['name']}/weights/best.pt"
        
        if os.path.exists(best_model_path):
            mlflow.log_artifact(best_model_path, "models")
            
            # Export YOLO to ONNX
            onnx_path = best_model_path.replace('.pt', '.onnx')
            model.export(format='onnx', imgsz=self.args.img_size)
            
            if os.path.exists(onnx_path):
                mlflow.log_artifact(onnx_path, "models")
        
        return mlflow.active_run().info.run_id
    
    def _register_model(self, model_name: str, run_id: str):
        """Register model in MLflow Model Registry"""
        client = MlflowClient()
        
        try:
            # Get model version
            model_uri = f"runs:/{run_id}/pytorch_model"
            
            # Register model
            model_version = mlflow.register_model(
                model_uri=model_uri,
                name=model_name,
                tags={
                    "architecture": self.args.model,
                    "purpose": "edge_inference",
                    "domain": "surveillance",
                    "training_timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"✅ Model registered: {model_name} v{model_version.version}")
            
            # Transition to staging if specified
            stage = os.getenv('MODEL_REGISTRY_STAGE', 'Staging')
            if stage in ['Staging', 'Production']:
                client.transition_model_version_stage(
                    name=model_name,
                    version=model_version.version,
                    stage=stage,
                    archive_existing_versions=False
                )
                logger.info(f"✅ Model transitioned to {stage}")
                
        except Exception as e:
            logger.error(f"❌ Failed to register model: {e}")
            raise

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='MLflow Edge Model Training Pipeline')
    
    parser.add_argument('--model', type=str, default='mobilenet_v3',
                      choices=['yolov8n', 'mobilenet_v3', 'efficientnet_b0'],
                      help='Model architecture to train')
    
    parser.add_argument('--epochs', type=int, default=50,
                      help='Number of training epochs')
    
    parser.add_argument('--batch-size', type=int, default=32,
                      help='Training batch size')
    
    parser.add_argument('--lr', type=float, default=0.001,
                      help='Learning rate')
    
    parser.add_argument('--img-size', type=int, default=224,
                      help='Input image size')
    
    parser.add_argument('--seed', type=int, default=42,
                      help='Random seed for reproducibility')
    
    return parser.parse_args()

def main():
    """Main training entry point"""
    args = parse_arguments()
    
    # Set random seeds for reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    
    logger.info("🚀 Starting MLflow Edge Model Training Pipeline")
    logger.info(f"Model: {args.model}")
    logger.info(f"Epochs: {args.epochs}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info(f"Learning Rate: {args.lr}")
    logger.info(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    
    try:
        trainer = ModelTrainer(args)
        run_id = trainer.train()
        
        logger.info(f"🎉 Training completed successfully!")
        logger.info(f"MLflow Run ID: {run_id}")
        logger.info(f"View results at: {os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")
        
    except Exception as e:
        logger.error(f"💥 Training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
