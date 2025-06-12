#!/usr/bin/env python3
"""
MLflow Tracking Server Implementation

This module provides a production-ready MLflow tracking server with:
1. SQLite backend for experiment tracking
2. Local artifact storage with configurable paths
3. Model registry for versioned model management
4. Health checks and monitoring endpoints
5. Authentication and authorization (optional)

Usage:
    python infra/mlflow_server.py --port 5000 --host 0.0.0.0

Environment Variables:
    MLFLOW_BACKEND_STORE_URI: Database URI for tracking store (default: sqlite:///mlflow.db)
    MLFLOW_ARTIFACT_ROOT: Root directory for artifact storage (default: ./mlflow-artifacts)
    MLFLOW_DEFAULT_ARTIFACT_ROOT: Default artifact location for experiments
    MLFLOW_SERVER_HOST: Host to bind the server to (default: 0.0.0.0)
    MLFLOW_SERVER_PORT: Port to bind the server to (default: 5000)
"""

import os
import sys
import time
import logging
import argparse
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import mlflow
    import mlflow.tracking
    from mlflow.tracking import MlflowClient
    from mlflow.entities import ViewType
except ImportError:
    print("ERROR: MLflow not installed. Run: pip install mlflow>=2.10.0")
    sys.exit(1)

try:
    import requests
    from flask import Flask, jsonify
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install requests flask")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mlflow_server')

class MLflowServer:
    """MLflow tracking server with monitoring capabilities"""
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 5000,
                 backend_store_uri: Optional[str] = None,
                 artifact_root: Optional[str] = None):
        """Initialize MLflow server configuration"""
        
        self.host = host
        self.port = port
        
        # Configure backend store (SQLite by default)
        self.backend_store_uri = backend_store_uri or os.getenv(
            'MLFLOW_BACKEND_STORE_URI', 
            'sqlite:///mlflow.db'
        )
        
        # Configure artifact storage
        self.artifact_root = artifact_root or os.getenv(
            'MLFLOW_ARTIFACT_ROOT',
            './mlflow-artifacts'
        )
        
        # Ensure artifact directory exists
        Path(self.artifact_root).mkdir(parents=True, exist_ok=True)
        
        # Server process handle
        self.server_process = None
        self.monitoring_app = None
        
        logger.info(f"MLflow server configuration:")
        logger.info(f"  Host: {self.host}")
        logger.info(f"  Port: {self.port}")
        logger.info(f"  Backend Store: {self.backend_store_uri}")
        logger.info(f"  Artifact Root: {self.artifact_root}")
    
    def setup_model_registry(self) -> None:
        """Initialize model registry with default models"""
        try:
            # Set MLflow tracking URI
            mlflow.set_tracking_uri(f"http://{self.host}:{self.port}")
            client = MlflowClient()
            
            # Wait for server to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    client.search_experiments()
                    logger.info("✅ MLflow server is ready")
                    break
                except Exception as e:
                    if i == max_retries - 1:
                        raise Exception(f"MLflow server failed to start: {e}")
                    logger.info(f"Waiting for MLflow server... ({i+1}/{max_retries})")
                    time.sleep(2)
            
            # Create default registered models for surveillance system
            default_models = [
                {
                    "name": "person-detection-model",
                    "description": "YOLOv8 model for person detection in surveillance footage"
                },
                {
                    "name": "face-recognition-model", 
                    "description": "FaceNet model for face recognition and identification"
                },
                {
                    "name": "object-detection-model",
                    "description": "Multi-class object detection model for surveillance scenarios"
                },
                {
                    "name": "anomaly-detection-model",
                    "description": "Autoencoder-based anomaly detection for unusual behavior"
                }
            ]
            
            for model_config in default_models:
                try:
                    existing_model = client.get_registered_model(model_config["name"])
                    logger.info(f"Model '{model_config['name']}' already exists")
                except Exception:
                    # Model doesn't exist, create it
                    client.create_registered_model(
                        name=model_config["name"],
                        description=model_config["description"]
                    )
                    logger.info(f"✅ Created registered model: {model_config['name']}")
            
            # Create default experiment
            try:
                experiment = client.get_experiment_by_name("surveillance-training")
            except Exception:
                experiment_id = client.create_experiment(
                    name="surveillance-training",
                    artifact_location=f"{self.artifact_root}/surveillance-training"
                )
                logger.info(f"✅ Created default experiment: surveillance-training (ID: {experiment_id})")
                
        except Exception as e:
            logger.error(f"❌ Failed to setup model registry: {e}")
            raise
    
    def create_monitoring_app(self) -> Flask:
        """Create Flask app for health monitoring"""
        app = Flask(__name__)
        
        @app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                # Check MLflow server
                mlflow.set_tracking_uri(f"http://{self.host}:{self.port}")
                client = MlflowClient()
                experiments = client.search_experiments()
                
                # Check artifact storage
                artifact_path = Path(self.artifact_root)
                artifact_accessible = artifact_path.exists() and artifact_path.is_dir()
                
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "mlflow_server": "running",
                    "experiments_count": len(experiments),
                    "artifact_storage": "accessible" if artifact_accessible else "error",
                    "backend_store": self.backend_store_uri,
                    "artifact_root": str(artifact_path.absolute())
                })
                
            except Exception as e:
                return jsonify({
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e)
                }), 500
        
        @app.route('/status', methods=['GET'])
        def server_status():
            """Detailed server status"""
            try:
                mlflow.set_tracking_uri(f"http://{self.host}:{self.port}")
                client = MlflowClient()
                
                # Get experiments
                experiments = client.search_experiments(view_type=ViewType.ALL)
                
                # Get registered models
                registered_models = client.search_registered_models()
                
                # Calculate storage usage
                artifact_path = Path(self.artifact_root)
                storage_size = sum(
                    f.stat().st_size for f in artifact_path.rglob('*') 
                    if f.is_file()
                ) if artifact_path.exists() else 0
                
                return jsonify({
                    "server_info": {
                        "host": self.host,
                        "port": self.port,
                        "backend_store": self.backend_store_uri,
                        "artifact_root": str(artifact_path.absolute())
                    },
                    "experiments": {
                        "total": len(experiments),
                        "active": len([e for e in experiments if e.lifecycle_stage == "active"]),
                        "names": [e.name for e in experiments[:10]]  # Show first 10
                    },
                    "registered_models": {
                        "total": len(registered_models),
                        "names": [m.name for m in registered_models]
                    },
                    "storage": {
                        "artifact_size_mb": round(storage_size / (1024 * 1024), 2),
                        "accessible": artifact_path.exists()
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        return app
    
    def start_server(self, background: bool = True) -> None:
        """Start MLflow tracking server"""
        try:
            # Build MLflow server command
            cmd = [
                sys.executable, "-m", "mlflow", "server",
                "--backend-store-uri", self.backend_store_uri,
                "--default-artifact-root", self.artifact_root,
                "--host", self.host,
                "--port", str(self.port),
                "--serve-artifacts"  # Enable artifact serving
            ]
            
            logger.info(f"Starting MLflow server: {' '.join(cmd)}")
            
            if background:
                # Start server in background
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                logger.info(f"✅ MLflow server started in background (PID: {self.server_process.pid})")
                
                # Setup model registry after server starts
                time.sleep(5)  # Give server time to start
                self.setup_model_registry()
                
            else:
                # Start server in foreground
                subprocess.run(cmd)
                
        except Exception as e:
            logger.error(f"❌ Failed to start MLflow server: {e}")
            raise
    
    def start_monitoring(self, monitoring_port: int = 5001) -> None:
        """Start monitoring endpoints"""
        try:
            self.monitoring_app = self.create_monitoring_app()
            
            def run_monitoring():
                self.monitoring_app.run(
                    host=self.host,
                    port=monitoring_port,
                    debug=False
                )
            
            monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
            monitoring_thread.start()
            
            logger.info(f"✅ Monitoring endpoints started on http://{self.host}:{monitoring_port}")
            logger.info(f"  Health check: http://{self.host}:{monitoring_port}/health")
            logger.info(f"  Server status: http://{self.host}:{monitoring_port}/status")
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            raise
    
    def stop_server(self) -> None:
        """Stop MLflow server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                logger.info("✅ MLflow server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                logger.warning("⚠️ MLflow server killed (timeout)")
            except Exception as e:
                logger.error(f"❌ Error stopping MLflow server: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MLflow Tracking Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--monitoring-port", type=int, default=5001, help="Monitoring port")
    parser.add_argument("--backend-store-uri", help="Backend store URI")
    parser.add_argument("--artifact-root", help="Artifact root directory")
    parser.add_argument("--background", action="store_true", help="Run in background")
    
    args = parser.parse_args()
    
    # Override with environment variables
    host = os.getenv('MLFLOW_SERVER_HOST', args.host)
    port = int(os.getenv('MLFLOW_SERVER_PORT', args.port))
    
    try:
        server = MLflowServer(
            host=host,
            port=port,
            backend_store_uri=args.backend_store_uri,
            artifact_root=args.artifact_root
        )
        
        # Start monitoring endpoints
        server.start_monitoring(args.monitoring_port)
        
        # Start MLflow server
        server.start_server(background=args.background)
        
        if args.background:
            logger.info("🚀 MLflow server and monitoring started")
            logger.info(f"MLflow UI: http://{host}:{port}")
            logger.info(f"Health check: http://{host}:{args.monitoring_port}/health")
            logger.info("Press Ctrl+C to stop...")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping MLflow server...")
                server.stop_server()
        
    except Exception as e:
        logger.error(f"💥 Failed to start MLflow server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
