#!/usr/bin/env python3
"""
Chaos Engineering Test Script

This script performs automated chaos engineering tests by:
1. Randomly selecting and deleting pods from Kafka StatefulSet and rag-service Deployment
2. Waiting for pods to be rescheduled and ready
3. Running health checks to verify system recovery

Usage:
    python infra/chaos_test.py

Environment Variables:
    KUBECONFIG: Path to Kubernetes config file
    MQTT_URL: MQTT broker URL for testing
    POSTGRES_URL: PostgreSQL connection string
    RAG_URL: RAG service URL for health checks
    NAMESPACE: Kubernetes namespace (default: chaos)
    KAFKA_STATEFULSET: Name of Kafka StatefulSet (default: kafka)
    RAG_DEPLOYMENT: Name of RAG service deployment (default: rag-service)
"""

import os
import sys
import json
import time
import random
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

# Kubernetes client
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    print("ERROR: kubernetes package not installed. Run: pip install kubernetes")
    sys.exit(1)

# Additional dependencies
try:
    import requests
    import paho.mqtt.client as mqtt
    import psycopg2
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install with: pip install requests paho-mqtt psycopg2-binary")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('chaos_test')

class ChaosTest:
    """Chaos engineering test orchestrator"""
    
    def __init__(self):
        """Initialize chaos test with configuration from environment"""
        self.namespace = os.getenv('NAMESPACE', 'chaos')
        self.kafka_statefulset = os.getenv('KAFKA_STATEFULSET', 'kafka')
        self.rag_deployment = os.getenv('RAG_DEPLOYMENT', 'rag-service')
        self.mqtt_url = os.getenv('MQTT_URL', 'tcp://localhost:1883')
        self.postgres_url = os.getenv('POSTGRES_URL', 'postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db')
        self.rag_url = os.getenv('RAG_URL', 'http://localhost:8004')
        
        # Initialize Kubernetes client
        try:
            if 'KUBECONFIG' in os.environ:
                config.load_kube_config(config_file=os.environ['KUBECONFIG'])
            else:
                config.load_incluster_config()
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("✅ Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kubernetes client: {e}")
            raise
    
    def get_statefulset_pods(self, statefulset_name: str) -> List[Dict]:
        """Get all pods from a StatefulSet"""
        try:
            # Get StatefulSet to find selector
            statefulset = self.apps_v1.read_namespaced_stateful_set(
                name=statefulset_name, 
                namespace=self.namespace
            )
            
            # Build label selector
            labels = statefulset.spec.selector.match_labels
            label_selector = ','.join([f"{k}={v}" for k, v in labels.items()])
            
            # Get pods
            pods = self.v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )
            
            return [{
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'ready': all(condition.status == "True" 
                           for condition in pod.status.conditions or []
                           if condition.type == "Ready")
            } for pod in pods.items]
            
        except ApiException as e:
            logger.error(f"❌ Failed to get StatefulSet pods: {e}")
            raise
    
    def get_deployment_pods(self, deployment_name: str) -> List[Dict]:
        """Get all pods from a Deployment"""
        try:
            # Get Deployment to find selector
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Build label selector
            labels = deployment.spec.selector.match_labels
            label_selector = ','.join([f"{k}={v}" for k, v in labels.items()])
            
            # Get pods
            pods = self.v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )
            
            return [{
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'ready': all(condition.status == "True" 
                           for condition in pod.status.conditions or []
                           if condition.type == "Ready")
            } for pod in pods.items]
            
        except ApiException as e:
            logger.error(f"❌ Failed to get Deployment pods: {e}")
            raise
    
    def delete_pod(self, pod_name: str) -> None:
        """Delete a specific pod"""
        try:
            self.v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions()            )
            logger.info(f"🔥 Deleted pod: {pod_name}")
        except ApiException as e:
            logger.error(f"❌ Failed to delete pod {pod_name}: {e}")
            raise
    
    def wait_for_pod_ready(self, pod_name_prefix: str, timeout_seconds: int = 60) -> bool:
        """Wait for a pod with the given prefix to be ready"""
        start_time = time.time()
        logger.info(f"⏳ Waiting for pod with prefix '{pod_name_prefix}' to be ready...")
        
        while time.time() - start_time < timeout_seconds:
            try:
                pods = self.v1.list_namespaced_pod(namespace=self.namespace)
                
                for pod in pods.items:
                    if pod.metadata.name.startswith(pod_name_prefix):
                        if pod.status.phase == "Running":
                            # Check readiness probes
                            if pod.status.conditions:
                                for condition in pod.status.conditions:
                                    if (condition.type == "Ready" and 
                                        condition.status == "True"):
                                        logger.info(f"✅ Pod {pod.metadata.name} is ready")
                                        return True
                
                time.sleep(5)
                
            except ApiException as e:
                logger.error(f"❌ Error checking pod status: {e}")
                time.sleep(5)
        
        logger.error(f"❌ Timeout waiting for pod with prefix '{pod_name_prefix}' to be ready")
        return False
    
    def test_mqtt_kafka_pipeline(self) -> bool:
        """Test MQTT → Kafka → Ingest pipeline"""
        logger.info("🧪 Testing MQTT → Kafka → Ingest pipeline...")
        
        test_event = {
            "camera_id": "chaos-test-camera",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "test_detection",
            "confidence": 0.95,
            "objects": ["person"],
            "metadata": {"chaos_test": True}
        }
        
        try:
            # Parse MQTT URL
            if self.mqtt_url.startswith('tcp://'):
                host = self.mqtt_url.replace('tcp://', '').split(':')[0]
                port = int(self.mqtt_url.replace('tcp://', '').split(':')[1]) if ':' in self.mqtt_url else 1883
            else:
                host, port = 'localhost', 1883
            
            # Publish test event to MQTT
            mqtt_client = mqtt.Client()
            mqtt_client.connect(host, port, 60)
            
            result = mqtt_client.publish(
                "camera/events/chaos-test", 
                json.dumps(test_event)
            )
            
            if result.rc != 0:
                logger.error(f"❌ Failed to publish MQTT message: {result.rc}")
                return False
            
            mqtt_client.disconnect()
            logger.info("📤 Published test event to MQTT")
              # Wait for message to be processed
            time.sleep(10)
            
            # Check if event was written to PostgreSQL
            try:
                conn = psycopg2.connect(self.postgres_url)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM events 
                    WHERE camera_id = %s 
                    AND timestamp > %s
                """, (
                    test_event['camera_id'],
                    (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
                ))
                
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                if count > 0:
                    logger.info("✅ Test event found in PostgreSQL")
                    return True
                else:
                    logger.error("❌ Test event not found in PostgreSQL")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to check PostgreSQL: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT test failed: {e}")
            return False
    
    def test_rag_service(self) -> bool:
        """Test RAG service health"""
        logger.info("🧪 Testing RAG service...")
        
        test_payload = {
            "query": "Show me recent person detections",
            "context_ids": []
        }
        
        try:
            response = requests.post(
                f"{self.rag_url}/rag/query",
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("✅ RAG service responding correctly")
                return True
            else:
                logger.error(f"❌ RAG service returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ RAG service test failed: {e}")
            return False
    
    def run_chaos_test(self) -> None:
        """Execute the complete chaos engineering test"""
        logger.info("🎯 Starting Chaos Engineering Test")
        logger.info("=" * 50)
        
        try:
            # Step 1: Get current pods
            logger.info("📋 Step 1: Discovering target pods...")
            
            kafka_pods = self.get_statefulset_pods(self.kafka_statefulset)
            rag_pods = self.get_deployment_pods(self.rag_deployment)
            
            if not kafka_pods:
                raise Exception(f"No Kafka pods found in StatefulSet {self.kafka_statefulset}")
            
            if not rag_pods:
                raise Exception(f"No RAG pods found in Deployment {self.rag_deployment}")
            
            logger.info(f"Found {len(kafka_pods)} Kafka pods and {len(rag_pods)} RAG pods")
            
            # Step 2: Select random pods to delete
            logger.info("🎲 Step 2: Selecting random pods for deletion...")
            
            kafka_target = random.choice(kafka_pods)
            rag_target = random.choice(rag_pods)
            
            logger.info(f"Selected Kafka pod: {kafka_target['name']}")
            logger.info(f"Selected RAG pod: {rag_target['name']}")
            
            # Step 3: Delete selected pods
            logger.info("💥 Step 3: Deleting selected pods...")
            
            self.delete_pod(kafka_target['name'])
            self.delete_pod(rag_target['name'])
            
            # Step 4: Wait for pods to be rescheduled and ready
            logger.info("⏳ Step 4: Waiting for pods to be rescheduled...")
            
            # Extract pod name prefixes for waiting
            kafka_prefix = '-'.join(kafka_target['name'].split('-')[:-1])
            rag_prefix = '-'.join(rag_target['name'].split('-')[:-1])
            
            kafka_ready = self.wait_for_pod_ready(kafka_prefix, timeout_seconds=60)
            rag_ready = self.wait_for_pod_ready(rag_prefix, timeout_seconds=60)
            
            if not kafka_ready:
                raise Exception("Kafka pod failed to become ready within timeout")
            
            if not rag_ready:
                raise Exception("RAG pod failed to become ready within timeout")
            
            # Step 5: Run health checks
            logger.info("🏥 Step 5: Running post-recovery health checks...")
            
            # Wait a bit more for services to fully initialize
            time.sleep(15)
            
            mqtt_test_passed = self.test_mqtt_kafka_pipeline()
            rag_test_passed = self.test_rag_service()
            
            # Step 6: Report results
            logger.info("📊 Step 6: Test Results")
            logger.info("-" * 30)
            
            if mqtt_test_passed and rag_test_passed:
                logger.info("🎉 ✅ ALL CHAOS TESTS PASSED!")
                logger.info("System successfully recovered from pod failures")
            else:
                error_msg = "❌ CHAOS TESTS FAILED:"
                if not mqtt_test_passed:
                    error_msg += "\n  - MQTT → Kafka → Ingest pipeline failed"
                if not rag_test_passed:
                    error_msg += "\n  - RAG service health check failed"
                
                logger.error(error_msg)
                raise Exception("Health checks failed after pod recovery")
            
        except Exception as e:
            logger.error(f"💥 Chaos test failed: {e}")
            raise

def main():
    """Main entry point"""
    try:
        chaos_test = ChaosTest()
        chaos_test.run_chaos_test()
        logger.info("🏁 Chaos engineering test completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Chaos engineering test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
