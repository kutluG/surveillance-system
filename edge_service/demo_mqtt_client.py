#!/usr/bin/env python3
"""
MQTT Client Integration Demo

This script demonstrates the MQTT client functionality by publishing
sample detection events to a local MQTT broker. It can be used to
verify the client works correctly before running the full test suite.

Usage:
    python demo_mqtt_client.py [--broker HOST] [--port PORT] [--count N]
"""
import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from mqtt_client import MQTTClient
except ImportError as e:
    print(f"❌ Cannot import mqtt_client: {e}")
    print("Make sure you're running this from the edge_service directory")
    sys.exit(1)


def create_sample_event(camera_id: str, event_id: int) -> Dict[str, Any]:
    """Create a sample detection event."""
    return {
        "camera_id": camera_id,
        "timestamp": datetime.now().isoformat(),
        "event_id": event_id,
        "event_type": "detection", 
        "detections": [
            {
                "label": "person",
                "confidence": 0.95,
                "bbox": {
                    "x": 100 + (event_id * 10),
                    "y": 200 + (event_id * 5),
                    "width": 50,
                    "height": 100
                }
            }
        ],
        "frame_count": 1000 + event_id,
        "processing_time_ms": 45.2,
        "model_version": "yolo_v8_edge",
        "anonymization_applied": True
    }


def main():
    parser = argparse.ArgumentParser(description="Demo MQTT client functionality")
    parser.add_argument("--broker", "-b", default="localhost", 
                       help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--port", "-p", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--count", "-c", type=int, default=5,
                       help="Number of events to publish (default: 5)")
    parser.add_argument("--topic", "-t", default="edge/detections",
                       help="MQTT topic to publish to (default: edge/detections)")
    parser.add_argument("--delay", "-d", type=float, default=1.0,
                       help="Delay between messages in seconds (default: 1.0)")
    
    args = parser.parse_args()
    
    print("🔌 MQTT Client Demo")
    print("=" * 30)
    print(f"Broker: {args.broker}:{args.port}")
    print(f"Topic: {args.topic}")
    print(f"Events: {args.count}")
    print()
    
    # Configure environment for insecure connection
    mqtt_config = {
        "MQTT_BROKER": args.broker,
        "MQTT_PORT_INSECURE": str(args.port),
        "MQTT_PORT": "8883",
        "MQTT_TLS_CA": "/nonexistent/ca.crt",
        "MQTT_TLS_CERT": "/nonexistent/client.crt",
        "MQTT_TLS_KEY": "/nonexistent/client.key"
    }
    
    # Apply configuration
    for key, value in mqtt_config.items():
        os.environ[key] = value
    
    try:
        # Create MQTT client
        print("🔗 Connecting to MQTT broker...")
        client = MQTTClient(client_id=f"demo_client_{int(time.time())}")
        
        print(f"✅ Connected ({('secure' if client.is_secure else 'insecure')} mode)")
        print()
        
        # Publish sample events
        print(f"📤 Publishing {args.count} detection events...")
        
        for i in range(args.count):
            event = create_sample_event(f"demo_cam_{i % 3}", i)
            
            try:
                client.publish_event(args.topic, event)
                print(f"  [{i+1}/{args.count}] Published event {i} from {event['camera_id']}")
                
                if i < args.count - 1:  # Don't delay after last message
                    time.sleep(args.delay)
                    
            except Exception as e:
                print(f"  ❌ Failed to publish event {i}: {e}")
        
        print()
        print(f"✅ Demo completed! Published {args.count} events to {args.topic}")
        print()
        print("💡 To subscribe and see the messages, run:")
        print(f"   mosquitto_sub -h {args.broker} -p {args.port} -t '{args.topic}' -v")
        
    except ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("💡 Make sure MQTT broker is running:")
        print(f"   mosquitto -p {args.port} -v")
        print("   OR")
        print(f"   docker run -it -p {args.port}:1883 eclipse-mosquitto:2.0")
        return 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
        return 130
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
        
    finally:
        # Clean up
        try:
            client.disconnect()
            print("🔌 Disconnected from broker")
        except:
            pass
    
    return 0


def test_broker_connection(host: str, port: int) -> bool:
    """Test if we can connect to the MQTT broker."""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


if __name__ == "__main__":
    # Quick broker connectivity check
    broker_host = sys.argv[sys.argv.index("--broker") + 1] if "--broker" in sys.argv else "localhost"
    broker_port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 1883
    
    print("🔍 Checking broker connectivity...")
    if test_broker_connection(broker_host, broker_port):
        print(f"✅ Broker {broker_host}:{broker_port} is reachable")
    else:
        print(f"⚠️  Cannot reach broker {broker_host}:{broker_port}")
        print("   The demo will still attempt to connect...")
    print()
    
    sys.exit(main())
