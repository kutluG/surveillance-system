"""
Tests for edge service setup and configuration.
Tests model installation, requirements consolidation, and configuration management.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestRequirementsConsolidation:
    """Test requirements.txt consolidation and validation"""
    
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists"""
        req_path = Path(__file__).parent.parent / "edge_service" / "requirements.txt"
        assert req_path.exists(), "requirements.txt should exist in edge_service directory"
    
    def test_requirements_no_duplicates(self):
        """Test that requirements.txt contains no duplicate packages"""
        req_path = Path(__file__).parent.parent / "edge_service" / "requirements.txt"
        
        with open(req_path, 'r') as f:
            lines = f.readlines()
        
        # Extract package names (everything before ==, >=, etc.)
        packages = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name before version specifier
                package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0]
                packages.append(package_name.lower())
          # Check for duplicates
        unique_packages = set(packages)
        assert len(packages) == len(unique_packages), f"Duplicate packages found: {set([x for x in packages if packages.count(x) > 1])}"
    
    def test_critical_packages_pinned(self):
        """Test that critical packages have pinned versions"""
        req_path = Path(__file__).parent.parent / "edge_service" / "requirements.txt"
        
        with open(req_path, 'r') as f:
            content = f.read()
        
        # Test for packages with or without extras
        critical_packages = {
            'opencv-python': 'opencv-python==',
            'paho-mqtt': 'paho-mqtt==',
            'fastapi': 'fastapi==',
            'uvicorn': 'uvicorn[standard]==',  # uvicorn has extras
            'pydantic': 'pydantic==',
            'numpy': 'numpy=='
        }
        
        for package, expected_format in critical_packages.items():
            assert expected_format in content, f"Critical package {package} should be pinned with format {expected_format}"
    
    def test_requirements_edge_service_removed(self):
        """Test that requirements_edge_service.txt is removed"""
        req_edge_path = Path(__file__).parent.parent / "edge_service" / "requirements_edge_service.txt"
        assert not req_edge_path.exists(), "requirements_edge_service.txt should be removed"


class TestDockerConfiguration:
    """Test Docker configuration files"""
    
    def test_dockerfile_build_args_present(self):
        """Test that Dockerfile contains the required build args"""
        dockerfile_path = Path(__file__).parent.parent / "edge_service" / "Dockerfile"
        
        if dockerfile_path.exists():
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            assert 'ARG MODEL_BASE_URL' in content, "Dockerfile should have MODEL_BASE_URL build arg"
            assert 'ARG DNN_MODEL_URL' in content, "Dockerfile should have DNN_MODEL_URL build arg"
            assert 'wget' in content or 'curl' in content, "Dockerfile should use wget or curl for downloads"
    
    def test_setup_face_models_removed(self):
        """Test that setup_face_models.py is removed"""
        setup_script_path = Path(__file__).parent.parent / "edge_service" / "setup_face_models.py"
        assert not setup_script_path.exists(), "setup_face_models.py should be removed"
    
    def test_docker_compose_has_build_args(self):
        """Test that docker-compose.yml contains build args"""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        if compose_path.exists():
            with open(compose_path, 'r') as f:
                content = f.read()
            
            assert 'MODEL_BASE_URL' in content, "docker-compose.yml should reference MODEL_BASE_URL"
            assert 'edge_service:' in content, "docker-compose.yml should contain edge_service"


class TestConfigurationFiles:
    """Test configuration file presence and structure"""
    
    def test_config_py_exists(self):
        """Test that config.py exists"""
        config_path = Path(__file__).parent.parent / "edge_service" / "config.py"
        assert config_path.exists(), "config.py should exist in edge_service directory"
    
    def test_config_has_settings_class(self):
        """Test that config.py contains EdgeServiceSettings class"""
        config_path = Path(__file__).parent.parent / "edge_service" / "config.py"
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        assert 'class EdgeServiceSettings' in content, "config.py should contain EdgeServiceSettings class"
        assert 'model_base_url' in content, "config.py should contain model_base_url setting"
        assert 'model_dir' in content, "config.py should contain model_dir setting"


class TestDocumentationUpdates:
    """Test documentation updates"""
    
    def test_face_anonymization_docs_exist(self):
        """Test that face anonymization documentation exists"""
        docs_path = Path(__file__).parent.parent / "docs" / "FACE_ANONYMIZATION.md"
        assert docs_path.exists(), "FACE_ANONYMIZATION.md should exist in docs directory"
    
    def test_face_anonymization_docs_has_model_section(self):
        """Test that documentation contains model installation section"""
        docs_path = Path(__file__).parent.parent / "docs" / "FACE_ANONYMIZATION.md"
        
        with open(docs_path, 'r') as f:
            content = f.read()
        
        assert '## Model Installation' in content, "Documentation should have Model Installation section"
        assert 'MODEL_BASE_URL' in content, "Documentation should mention MODEL_BASE_URL"
        assert 'docker build' in content, "Documentation should mention docker build"


class TestModelFileSimulation:
    """Test model file handling simulation"""
    
    def test_model_files_simulation(self):
        """Simulate model file creation and validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir) / "models"
            models_dir.mkdir()
            
            # Simulate model file creation (as would happen in Docker build)
            test_files = {
                'haarcascade_frontalface_default.xml': b'<?xml version="1.0"?>\n<opencv_storage>\n</opencv_storage>',
                'opencv_face_detector.pbtxt': b'input: "data"\ninput_shape {\n  dim: 1\n}',
                'opencv_face_detector_uint8.pb': b'\x08\x01\x12\x04test'  # Mock binary content
            }
            
            for filename, content in test_files.items():
                file_path = models_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            # Verify files exist and are not empty
            for filename in test_files.keys():
                file_path = models_dir / filename
                assert file_path.exists(), f"Model file {filename} should exist"
                assert file_path.stat().st_size > 0, f"Model file {filename} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
