"""
Pytest configuration and fixtures for edge service tests.
"""
import os
import sys
import pytest
import socket
import subprocess
import time
import tempfile
import shutil
import signal
import psutil
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import patch
from contextlib import contextmanager
import signal
import psutil
from contextlib import contextmanager

# Add the parent directory to the path to import edge service modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="session")
def mosquitto_broker() -> Generator[Dict[str, Any], None, None]:
    """
    Start an ephemeral Mosquitto MQTT broker for testing.
    
    This fixture uses subprocess to start a mosquitto broker on a random port.
    Falls back to Docker if mosquitto is not installed locally.
    """
    broker_port = find_free_port()
    config_dir = tempfile.mkdtemp()
    config_file = os.path.join(config_dir, "mosquitto.conf")
    
    # Create minimal mosquitto configuration
    config_content = f"""
# Mosquitto test configuration
port {broker_port}
allow_anonymous true
listener {broker_port}
protocol mqtt
"""
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    broker_process = None
    docker_container = None
    
    try:
        # Try to start mosquitto directly
        try:
            broker_process = subprocess.Popen([
                "mosquitto", "-c", config_file
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a bit for the broker to start
            time.sleep(2)
            
            # Check if process is still running
            if broker_process.poll() is not None:
                raise subprocess.CalledProcessError(1, "mosquitto")
                
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Fall back to Docker if mosquitto is not installed
            try:
                docker_container = f"test_mosquitto_{broker_port}"
                subprocess.run([
                    "docker", "run", "-d", "--name", docker_container,
                    "-p", f"{broker_port}:1883",
                    "eclipse-mosquitto:2.0"
                ], check=True, capture_output=True)
                
                # Wait for container to be ready
                time.sleep(5)
                
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                pytest.skip(f"Cannot start MQTT broker: {e}")
        
        yield {
            "host": "localhost",
            "port": broker_port,
            "url": f"mqtt://localhost:{broker_port}"
        }
        
    finally:
        # Cleanup
        if broker_process:
            broker_process.terminate()
            broker_process.wait()
        
        if docker_container:
            try:
                subprocess.run(["docker", "stop", docker_container], 
                             check=False, capture_output=True)
                subprocess.run(["docker", "rm", docker_container], 
                             check=False, capture_output=True)
            except Exception:
                pass
        
        # Clean up config directory
        shutil.rmtree(config_dir, ignore_errors=True)


@pytest.fixture
def mqtt_config(mosquitto_broker: Dict[str, Any]) -> Dict[str, str]:
    """
    Provide MQTT configuration for tests.
    """
    return {
        "MQTT_BROKER": mosquitto_broker["host"],
        "MQTT_PORT_INSECURE": str(mosquitto_broker["port"]),
        "MQTT_PORT": "8883",  # Not used in tests (secure)
        "MQTT_TLS_CA": "/nonexistent/ca.crt",
        "MQTT_TLS_CERT": "/nonexistent/client.crt", 
        "MQTT_TLS_KEY": "/nonexistent/client.key"
    }


@pytest.fixture
def mock_certificates_unavailable():
    """
    Mock certificate files as unavailable to force insecure connection.
    """
    with patch('os.path.exists', return_value=False), \
         patch('os.path.isfile', return_value=False):
        yield


@pytest.fixture
def sample_detection_event() -> Dict[str, Any]:
    """
    Provide a sample detection event for testing.
    """
    from datetime import datetime
    
    return {
        "camera_id": "cam1",
        "timestamp": datetime.now().isoformat(),
        "detections": [
            {
                "label": "person",
                "confidence": 0.95,
                "bbox": {
                    "x": 100,
                    "y": 200,
                    "width": 50,
                    "height": 100
                }
            }
        ],
        "frame_count": 12345,
        "event_type": "detection"
    }


@pytest.fixture
def temp_cert_dir():
    """
    Create a temporary directory with mock certificate files.
    """
    cert_dir = tempfile.mkdtemp()
    
    # Create mock certificate files
    cert_files = ["ca.crt", "client.crt", "client.key"]
    for cert_file in cert_files:
        cert_path = os.path.join(cert_dir, cert_file)
        with open(cert_path, 'w') as f:
            f.write("# Mock certificate file for testing\n")
    
    yield cert_dir
    
    # Cleanup
    shutil.rmtree(cert_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mosquitto_broker_restartable() -> Generator[Dict[str, Any], None, None]:
    """
    Start a restartable Mosquitto MQTT broker for reconnection testing.
    
    This fixture provides start/stop/restart functionality for testing
    reconnection logic by actually stopping and starting the broker process.
    """
    broker_port = find_free_port()
    config_dir = tempfile.mkdtemp()
    config_file = os.path.join(config_dir, "mosquitto_restartable.conf")
    
    # Create minimal mosquitto configuration
    config_content = f"""
# Mosquitto restartable test configuration
port {broker_port}
allow_anonymous true
listener {broker_port} 0.0.0.0
protocol mqtt
persistence false
retained_persistence false
"""
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    broker_process = None
    docker_container = None
    use_docker = False
    
    def start_broker():
        nonlocal broker_process, docker_container, use_docker
        
        if use_docker:
            # Start with Docker
            try:
                docker_container = f"test_mosquitto_restart_{broker_port}_{int(time.time())}"
                subprocess.run([
                    "docker", "run", "-d", "--name", docker_container,
                    "-p", f"{broker_port}:1883",
                    "eclipse-mosquitto:2.0"
                ], check=True, capture_output=True)
                time.sleep(3)  # Wait for container to be ready
                return True
            except Exception as e:
                print(f"Failed to start Docker broker: {e}")
                return False
        else:
            # Start with subprocess
            try:
                broker_process = subprocess.Popen([
                    "mosquitto", "-c", config_file
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(2)  # Wait for broker to start
                
                # Check if process is still running
                if broker_process.poll() is not None:
                    return False
                return True
            except Exception as e:
                print(f"Failed to start subprocess broker: {e}")
                return False
    
    def stop_broker():
        nonlocal broker_process, docker_container
        
        if use_docker and docker_container:
            try:
                subprocess.run(["docker", "stop", docker_container], 
                             check=True, capture_output=True, timeout=10)
                print(f"Stopped Docker container {docker_container}")
            except Exception as e:
                print(f"Error stopping Docker container: {e}")
        elif broker_process:
            try:
                broker_process.terminate()
                broker_process.wait(timeout=5)
                print("Stopped subprocess broker")
            except subprocess.TimeoutExpired:
                broker_process.kill()
                broker_process.wait()
                print("Killed subprocess broker")
            except Exception as e:
                print(f"Error stopping subprocess broker: {e}")
    
    def restart_broker():
        stop_broker()
        time.sleep(1)
        return start_broker()
    
    def cleanup():
        stop_broker()
        
        if docker_container:
            try:
                subprocess.run(["docker", "rm", "-f", docker_container], 
                             check=False, capture_output=True)
            except Exception:
                pass
        
        # Clean up config directory
        shutil.rmtree(config_dir, ignore_errors=True)
    
    try:
        # Try to start with subprocess first, fall back to Docker
        if not start_broker():
            use_docker = True
            if not start_broker():
                pytest.skip("Cannot start restartable MQTT broker (tried subprocess and Docker)")
        
        yield {
            "host": "localhost",
            "port": broker_port,
            "url": f"mqtt://localhost:{broker_port}",
            "stop": stop_broker,
            "start": start_broker,
            "restart": restart_broker
        }
        
    finally:
        cleanup()


@pytest.fixture
def testcontainers_mosquitto_broker():
    """
    Alternative MQTT broker fixture using testcontainers-python.
    
    This fixture uses testcontainers to manage the MQTT broker lifecycle,
    providing more reliable container management for CI/CD environments.
    """
    try:
        from testcontainers.compose import DockerCompose
        from testcontainers.core.container import DockerContainer
        from testcontainers.core.waiting_utils import wait_for_logs
    except ImportError:
        pytest.skip("testcontainers-python not available")
    
    # Use Eclipse Mosquitto container
    mosquitto_port = 1883
    
    with DockerContainer("eclipse-mosquitto:2.0") \
            .with_exposed_ports(mosquitto_port) \
            .with_command("mosquitto -c /mosquitto-no-auth.conf") as container:
        
        # Wait for the broker to be ready
        time.sleep(3)
        
        # Get the mapped port
        mapped_port = container.get_exposed_port(mosquitto_port)
        
        yield {
            "host": "localhost", 
            "port": int(mapped_port),
            "url": f"mqtt://localhost:{mapped_port}",
            "container": container
        }
