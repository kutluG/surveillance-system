"""
Tests for chaos engineering script

These tests mock the Kubernetes client and external services to verify
that the chaos engineering script behaves correctly under various scenarios.
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

# Import the chaos test module
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'infra'))

try:
    from chaos_test import ChaosTest
except ImportError:
    pytest.skip("chaos_test module not available", allow_module_level=True)


class TestChaosEngineering:
    """Test suite for chaos engineering functionality"""

    @pytest.fixture
    def mock_k8s_clients(self):
        """Mock Kubernetes clients"""
        with patch('chaos_test.client') as mock_client, \
             patch('chaos_test.config') as mock_config:
            
            # Mock V1 API client
            mock_v1 = Mock()
            mock_client.CoreV1Api.return_value = mock_v1
            
            # Mock Apps V1 API client
            mock_apps_v1 = Mock()
            mock_client.AppsV1Api.return_value = mock_apps_v1
            
            # Mock delete options
            mock_client.V1DeleteOptions.return_value = Mock()
            
            yield {
                'v1': mock_v1,
                'apps_v1': mock_apps_v1,
                'config': mock_config,
                'client': mock_client
            }

    @pytest.fixture
    def chaos_test_instance(self, mock_k8s_clients):
        """Create a ChaosTest instance with mocked dependencies"""
        with patch.dict(os.environ, {
            'NAMESPACE': 'test-namespace',
            'KAFKA_STATEFULSET': 'test-kafka',
            'RAG_DEPLOYMENT': 'test-rag',
            'MQTT_URL': 'tcp://localhost:1883',
            'POSTGRES_URL': 'postgresql://user:pass@localhost:5432/db',
            'RAG_URL': 'http://localhost:8004'
        }):
            return ChaosTest()

    def test_get_statefulset_pods_success(self, chaos_test_instance, mock_k8s_clients):
        """Test successful retrieval of StatefulSet pods"""
        # Mock StatefulSet response
        mock_statefulset = Mock()
        mock_statefulset.spec.selector.match_labels = {'app': 'kafka'}
        mock_k8s_clients['apps_v1'].read_namespaced_stateful_set.return_value = mock_statefulset
        
        # Mock pod list response
        mock_pod = Mock()
        mock_pod.metadata.name = 'kafka-0'
        mock_pod.status.phase = 'Running'
        
        # Mock ready condition
        mock_condition = Mock()
        mock_condition.type = 'Ready'
        mock_condition.status = 'True'
        mock_pod.status.conditions = [mock_condition]
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        mock_k8s_clients['v1'].list_namespaced_pod.return_value = mock_pod_list
        
        # Execute test
        pods = chaos_test_instance.get_statefulset_pods('test-kafka')
        
        # Verify results
        assert len(pods) == 1
        assert pods[0]['name'] == 'kafka-0'
        assert pods[0]['status'] == 'Running'
        assert pods[0]['ready'] is True
        
        # Verify API calls
        mock_k8s_clients['apps_v1'].read_namespaced_stateful_set.assert_called_once_with(
            name='test-kafka',
            namespace='test-namespace'
        )
        mock_k8s_clients['v1'].list_namespaced_pod.assert_called_once_with(
            namespace='test-namespace',
            label_selector='app=kafka'
        )

    def test_get_deployment_pods_success(self, chaos_test_instance, mock_k8s_clients):
        """Test successful retrieval of Deployment pods"""
        # Mock Deployment response
        mock_deployment = Mock()
        mock_deployment.spec.selector.match_labels = {'app': 'rag-service'}
        mock_k8s_clients['apps_v1'].read_namespaced_deployment.return_value = mock_deployment
        
        # Mock pod list response
        mock_pod = Mock()
        mock_pod.metadata.name = 'rag-service-abc123'
        mock_pod.status.phase = 'Running'
        
        # Mock ready condition
        mock_condition = Mock()
        mock_condition.type = 'Ready'
        mock_condition.status = 'True'
        mock_pod.status.conditions = [mock_condition]
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        mock_k8s_clients['v1'].list_namespaced_pod.return_value = mock_pod_list
        
        # Execute test
        pods = chaos_test_instance.get_deployment_pods('test-rag')
        
        # Verify results
        assert len(pods) == 1
        assert pods[0]['name'] == 'rag-service-abc123'
        assert pods[0]['status'] == 'Running'
        assert pods[0]['ready'] is True

    def test_delete_pod_success(self, chaos_test_instance, mock_k8s_clients):
        """Test successful pod deletion"""
        # Execute test
        chaos_test_instance.delete_pod('test-pod-123')
        
        # Verify API call
        mock_k8s_clients['v1'].delete_namespaced_pod.assert_called_once_with(
            name='test-pod-123',
            namespace='test-namespace',
            body=mock_k8s_clients['client'].V1DeleteOptions()
        )

    @patch('chaos_test.time.sleep')
    def test_wait_for_pod_ready_success(self, mock_sleep, chaos_test_instance, mock_k8s_clients):
        """Test successful waiting for pod to become ready"""
        # Mock pod list responses (first call: not ready, second call: ready)
        mock_pod = Mock()
        mock_pod.metadata.name = 'kafka-0-new'
        mock_pod.status.phase = 'Running'
        
        # First call: not ready
        mock_condition_not_ready = Mock()
        mock_condition_not_ready.type = 'Ready'
        mock_condition_not_ready.status = 'False'
        
        # Second call: ready
        mock_condition_ready = Mock()
        mock_condition_ready.type = 'Ready'
        mock_condition_ready.status = 'True'
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        
        # Configure side effects for multiple calls
        def mock_list_pods(*args, **kwargs):
            if mock_k8s_clients['v1'].list_namespaced_pod.call_count == 1:
                mock_pod.status.conditions = [mock_condition_not_ready]
            else:
                mock_pod.status.conditions = [mock_condition_ready]
            return mock_pod_list
        
        mock_k8s_clients['v1'].list_namespaced_pod.side_effect = mock_list_pods
        
        # Execute test
        result = chaos_test_instance.wait_for_pod_ready('kafka-0', timeout_seconds=60)
        
        # Verify result
        assert result is True
        assert mock_k8s_clients['v1'].list_namespaced_pod.call_count >= 2

    @patch('chaos_test.time.sleep')
    @patch('chaos_test.time.time')
    def test_wait_for_pod_ready_timeout(self, mock_time, mock_sleep, chaos_test_instance, mock_k8s_clients):
        """Test timeout when waiting for pod to become ready"""
        # Mock time progression
        mock_time.side_effect = [0, 30, 60, 90]  # Simulate timeout
        
        # Mock pod list response (never becomes ready)
        mock_pod = Mock()
        mock_pod.metadata.name = 'kafka-0-stuck'
        mock_pod.status.phase = 'Pending'
        mock_pod.status.conditions = []
        
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        mock_k8s_clients['v1'].list_namespaced_pod.return_value = mock_pod_list
        
        # Execute test
        result = chaos_test_instance.wait_for_pod_ready('kafka-0', timeout_seconds=60)
        
        # Verify timeout
        assert result is False

    @patch('chaos_test.mqtt.Client')
    @patch('chaos_test.psycopg2.connect')
    def test_mqtt_kafka_pipeline_success(self, mock_psycopg2, mock_mqtt_client, chaos_test_instance):
        """Test successful MQTT → Kafka → Ingest pipeline"""
        # Mock MQTT client
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        # Mock successful publish
        mock_result = Mock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        
        # Mock PostgreSQL connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)  # Event found
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.return_value = mock_conn
        
        # Execute test
        with patch('chaos_test.time.sleep'):  # Skip actual sleep
            result = chaos_test_instance.test_mqtt_kafka_pipeline()
        
        # Verify result
        assert result is True
        
        # Verify MQTT publish
        mock_client.publish.assert_called_once()
        
        # Verify PostgreSQL query
        mock_cursor.execute.assert_called_once()
        assert 'chaos-test-camera' in mock_cursor.execute.call_args[0][1][0]

    @patch('chaos_test.mqtt.Client')
    @patch('chaos_test.psycopg2.connect')
    def test_mqtt_kafka_pipeline_failure(self, mock_psycopg2, mock_mqtt_client, chaos_test_instance):
        """Test MQTT → Kafka → Ingest pipeline failure"""
        # Mock MQTT client
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        # Mock successful publish
        mock_result = Mock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        
        # Mock PostgreSQL connection - no events found
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (0,)  # No events found
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.return_value = mock_conn
        
        # Execute test
        with patch('chaos_test.time.sleep'):  # Skip actual sleep
            result = chaos_test_instance.test_mqtt_kafka_pipeline()
        
        # Verify failure
        assert result is False

    @patch('chaos_test.requests.post')
    def test_rag_service_success(self, mock_post, chaos_test_instance):
        """Test successful RAG service health check"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Execute test
        result = chaos_test_instance.test_rag_service()
        
        # Verify result
        assert result is True
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['query'] == 'Show me recent person detections'

    @patch('chaos_test.requests.post')
    def test_rag_service_failure(self, mock_post, chaos_test_instance):
        """Test RAG service health check failure"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Execute test
        result = chaos_test_instance.test_rag_service()
        
        # Verify failure
        assert result is False

    @patch('chaos_test.requests.post')
    def test_rag_service_exception(self, mock_post, chaos_test_instance):
        """Test RAG service health check with exception"""
        # Mock exception
        mock_post.side_effect = Exception("Connection failed")
        
        # Execute test
        result = chaos_test_instance.test_rag_service()
        
        # Verify failure
        assert result is False

    def test_run_chaos_test_no_pods_found(self, chaos_test_instance, mock_k8s_clients):
        """Test chaos test failure when no pods are found"""
        # Mock empty pod lists
        mock_k8s_clients['apps_v1'].read_namespaced_stateful_set.side_effect = Exception("StatefulSet not found")
        
        # Execute test and expect failure
        with pytest.raises(Exception) as exc_info:
            chaos_test_instance.run_chaos_test()
        
        assert "StatefulSet not found" in str(exc_info.value)

    @patch('chaos_test.random.choice')
    def test_run_chaos_test_pod_selection(self, mock_choice, chaos_test_instance, mock_k8s_clients):
        """Test that chaos test correctly selects random pods"""
        # Mock StatefulSet and Deployment responses
        mock_statefulset = Mock()
        mock_statefulset.spec.selector.match_labels = {'app': 'kafka'}
        mock_k8s_clients['apps_v1'].read_namespaced_stateful_set.return_value = mock_statefulset
        
        mock_deployment = Mock()
        mock_deployment.spec.selector.match_labels = {'app': 'rag'}
        mock_k8s_clients['apps_v1'].read_namespaced_deployment.return_value = mock_deployment
        
        # Mock pod lists
        kafka_pod = {'name': 'kafka-0', 'status': 'Running', 'ready': True}
        rag_pod = {'name': 'rag-abc123', 'status': 'Running', 'ready': True}
        
        mock_pod_list = Mock()
        mock_pod_list.items = []
        mock_k8s_clients['v1'].list_namespaced_pod.return_value = mock_pod_list
        
        # Configure random.choice to return specific pods
        mock_choice.side_effect = [kafka_pod, rag_pod]
        
        # Mock other methods to avoid full execution
        with patch.object(chaos_test_instance, 'delete_pod'), \
             patch.object(chaos_test_instance, 'wait_for_pod_ready', return_value=True), \
             patch.object(chaos_test_instance, 'test_mqtt_kafka_pipeline', return_value=True), \
             patch.object(chaos_test_instance, 'test_rag_service', return_value=True), \
             patch.object(chaos_test_instance, 'get_statefulset_pods', return_value=[kafka_pod]), \
             patch.object(chaos_test_instance, 'get_deployment_pods', return_value=[rag_pod]), \
             patch('chaos_test.time.sleep'):
            
            # Execute test
            chaos_test_instance.run_chaos_test()
            
            # Verify random selection was called
            assert mock_choice.call_count == 2

    def test_run_chaos_test_health_check_failure(self, chaos_test_instance, mock_k8s_clients):
        """Test chaos test failure when health checks fail"""
        # Mock successful pod operations but failed health checks
        with patch.object(chaos_test_instance, 'get_statefulset_pods', 
                         return_value=[{'name': 'kafka-0', 'status': 'Running', 'ready': True}]), \
             patch.object(chaos_test_instance, 'get_deployment_pods', 
                         return_value=[{'name': 'rag-abc123', 'status': 'Running', 'ready': True}]), \
             patch.object(chaos_test_instance, 'delete_pod'), \
             patch.object(chaos_test_instance, 'wait_for_pod_ready', return_value=True), \
             patch.object(chaos_test_instance, 'test_mqtt_kafka_pipeline', return_value=False), \
             patch.object(chaos_test_instance, 'test_rag_service', return_value=True), \
             patch('chaos_test.time.sleep'), \
             patch('chaos_test.random.choice') as mock_choice:
            
            # Configure random choice
            mock_choice.side_effect = [
                {'name': 'kafka-0', 'status': 'Running', 'ready': True},
                {'name': 'rag-abc123', 'status': 'Running', 'ready': True}
            ]
            
            # Execute test and expect failure
            with pytest.raises(Exception) as exc_info:
                chaos_test_instance.run_chaos_test()
            
            assert "Health checks failed" in str(exc_info.value)


class TestChaosTestIntegration:
    """Integration-style tests for chaos engineering"""

    @patch.dict(os.environ, {
        'NAMESPACE': 'test-chaos',
        'KAFKA_STATEFULSET': 'kafka-test',
        'RAG_DEPLOYMENT': 'rag-test'
    })
    def test_environment_configuration(self):
        """Test that environment variables are properly loaded"""
        with patch('chaos_test.config'), \
             patch('chaos_test.client.CoreV1Api'), \
             patch('chaos_test.client.AppsV1Api'):
            
            chaos_test = ChaosTest()
            
            assert chaos_test.namespace == 'test-chaos'
            assert chaos_test.kafka_statefulset == 'kafka-test'
            assert chaos_test.rag_deployment == 'rag-test'

    def test_kubernetes_client_initialization_failure(self):
        """Test proper error handling when Kubernetes client fails to initialize"""
        with patch('chaos_test.config.load_kube_config', side_effect=Exception("No config found")), \
             patch('chaos_test.config.load_incluster_config', side_effect=Exception("Not in cluster")):
              with pytest.raises(Exception):
                ChaosTest()

    def test_logging_integration(self, mocker):
        """Test that logging is properly integrated throughout the chaos test"""
        mock_logger = mocker.patch('chaos_test.logger')
        
        with patch('chaos_test.config'), \
             patch('chaos_test.client.CoreV1Api'), \
             patch('chaos_test.client.AppsV1Api'), \
             patch.dict(os.environ, {'NAMESPACE': 'test-logging'}):
            
            chaos_test = ChaosTest()
            
            # Verify initialization logging
            mock_logger.info.assert_called_with("✅ Kubernetes client initialized successfully")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
