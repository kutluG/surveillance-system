"""
Health check script for deployment verification.
"""
import requests
import time
import sys
from typing import Dict, List, Tuple

class HealthChecker:
    """Health checker for surveillance system deployment."""
    
    def __init__(self):
        self.services = {
            "edge_service": {"url": "http://localhost:8001", "critical": True},
            "mqtt_kafka_bridge": {"url": "http://localhost:8002", "critical": True},
            "ingest_service": {"url": "http://localhost:8003", "critical": True},
            "rag_service": {"url": "http://localhost:8004", "critical": False},
            "prompt_service": {"url": "http://localhost:8005", "critical": False},
            "rulegen_service": {"url": "http://localhost:8006", "critical": True},
            "notifier": {"url": "http://localhost:8007", "critical": True},
            "vms_service": {"url": "http://localhost:8008", "critical": False},
        }
        
        self.infrastructure = {
            "postgres": {"url": "http://localhost:5432", "check": self._check_postgres},
            "redis": {"url": "http://localhost:6379", "check": self._check_redis},
            "kafka": {"url": "http://localhost:9092", "check": self._check_kafka},
            "weaviate": {"url": "http://localhost:8080", "check": self._check_weaviate},
            "prometheus": {"url": "http://localhost:9090", "check": self._check_prometheus},
            "grafana": {"url": "http://localhost:3000", "check": self._check_grafana},
        }
    
    def check_service_health(self, service_name: str, config: Dict) -> Tuple[bool, str, float]:
        """Check health of a single service."""
        url = f"{config['url']}/health"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "ok":
                        return True, "Healthy", response_time
                    else:
                        return False, f"Unhealthy status: {data}", response_time
                except:
                    return True, "Healthy (non-JSON response)", response_time
            else:
                return False, f"HTTP {response.status_code}", response_time
                
        except requests.exceptions.ConnectionError:
            return False, "Connection refused", 0
        except requests.exceptions.Timeout:
            return False, "Timeout", 10
        except Exception as e:
            return False, str(e), 0
    
    def _check_postgres(self) -> Tuple[bool, str]:
        """Check PostgreSQL health."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="events_db",
                user="user",
                password="password",
                connect_timeout=5
            )
            conn.close()
            return True, "Connected"
        except Exception as e:
            return False, str(e)
    
    def _check_redis(self) -> Tuple[bool, str]:
        """Check Redis health."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
            r.ping()
            return True, "Connected"
        except Exception as e:
            return False, str(e)
    
    def _check_kafka(self) -> Tuple[bool, str]:
        """Check Kafka health."""
        try:
            from confluent_kafka.admin import AdminClient
            admin = AdminClient({'bootstrap.servers': 'localhost:9092'})
            metadata = admin.list_topics(timeout=5)
            return True, f"Connected, {len(metadata.topics)} topics"
        except Exception as e:
            return False, str(e)
    
    def _check_weaviate(self) -> Tuple[bool, str]:
        """Check Weaviate health."""
        try:
            response = requests.get("http://localhost:8080/v1/.well-known/ready", timeout=5)
            if response.status_code == 200:
                return True, "Ready"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def _check_prometheus(self) -> Tuple[bool, str]:
        """Check Prometheus health."""
        try:
            response = requests.get("http://localhost:9090/-/ready", timeout=5)
            if response.status_code == 200:
                return True, "Ready"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def _check_grafana(self) -> Tuple[bool, str]:
        """Check Grafana health."""
        try:
            response = requests.get("http://localhost:3000/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return True, f"Version {data.get('version', 'unknown')}"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def run_full_health_check(self) -> Dict:
        """Run complete health check."""
        results = {
            "timestamp": time.time(),
            "services": {},
            "infrastructure": {},
            "summary": {}
        }
        
        print("🔍 Running comprehensive health check...")
        print("=" * 50)
        
        # Check application services
        print("\n📱 Application Services:")
        service_results = []
        
        for service_name, config in self.services.items():
            healthy, message, response_time = self.check_service_health(service_name, config)
            
            results["services"][service_name] = {
                "healthy": healthy,
                "message": message,
                "response_time": response_time,
                "critical": config["critical"]
            }
            
            status_icon = "✅" if healthy else "❌"
            critical_marker = " (CRITICAL)" if config["critical"] else ""
            print(f"  {status_icon} {service_name}{critical_marker}: {message} ({response_time:.3f}s)")
            
            service_results.append(healthy)
        
        # Check infrastructure
        print("\n🏗️  Infrastructure Services:")
        infra_results = []
        
        for service_name, config in self.infrastructure.items():
            healthy, message = config["check"]()
            
            results["infrastructure"][service_name] = {
                "healthy": healthy,
                "message": message
            }
            
            status_icon = "✅" if healthy else "❌"
            print(f"  {status_icon} {service_name}: {message}")
            
            infra_results.append(healthy)
        
        # Calculate summary
        healthy_services = sum(service_results)
        total_services = len(service_results)
        critical_services = [name for name, config in self.services.items() 
                           if config["critical"] and results["services"][name]["healthy"]]
        
        healthy_infra = sum(infra_results)
        total_infra = len(infra_results)
        
        results["summary"] = {
            "services_healthy": healthy_services,
            "services_total": total_services,
            "services_success_rate": healthy_services / total_services,
            "critical_services_healthy": len(critical_services),
            "infrastructure_healthy": healthy_infra,
            "infrastructure_total": total_infra,
            "infrastructure_success_rate": healthy_infra / total_infra,
            "overall_healthy": healthy_services == total_services and healthy_infra == total_infra
        }
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"  Services: {healthy_services}/{total_services} healthy ({results['summary']['services_success_rate']:.1%})")
        print(f"  Infrastructure: {healthy_infra}/{total_infra} healthy ({results['summary']['infrastructure_success_rate']:.1%})")
        
        if results["summary"]["overall_healthy"]:
            print(f"  🎉 System is fully operational!")
        else:
            print(f"  ⚠️  System has issues that need attention")
        
        return results
    
    def wait_for_readiness(self, max_wait: int = 300, check_interval: int = 10) -> bool:
        """Wait for system to become ready."""
        print(f"⏳ Waiting for system readiness (max {max_wait}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            results = self.run_full_health_check()
            
            if results["summary"]["overall_healthy"]:
                print(f"✅ System ready after {time.time() - start_time:.1f}s")
                return True
            
            # Check critical services at minimum
            critical_healthy = all(
                results["services"][name]["healthy"] 
                for name, config in self.services.items() 
                if config["critical"]
            )
            
            if critical_healthy:
                print(f"✅ Critical services ready after {time.time() - start_time:.1f}s")
                return True
            
            print(f"⏳ Waiting... ({time.time() - start_time:.1f}s elapsed)")
            time.sleep(check_interval)
        
        print(f"❌ System not ready after {max_wait}s")
        return False
    
    def run_smoke_tests(self) -> bool:
        """Run basic smoke tests."""
        print("\n🧪 Running smoke tests...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test 1: Health endpoints
        total_tests += 1
        try:
            all_healthy = True
            for service_name, config in self.services.items():
                if config["critical"]:
                    healthy, _, _ = self.check_service_health(service_name, config)
                    if not healthy:
                        all_healthy = False
                        break
            
            if all_healthy:
                print("  ✅ All critical services healthy")
                tests_passed += 1
            else:
                print("  ❌ Some critical services unhealthy")
        except Exception as e:
            print(f"  ❌ Health check test failed: {e}")
        
        # Test 2: Basic API functionality
        total_tests += 1
        try:
            response = requests.get("http://localhost:8005/health", timeout=5)
            if response.status_code == 200:
                print("  ✅ API endpoints responding")
                tests_passed += 1
            else:
                print(f"  ❌ API test failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ API test failed: {e}")
        
        # Test 3: Database connectivity
        total_tests += 1
        try:
            healthy, message = self._check_postgres()
            if healthy:
                print("  ✅ Database connectivity")
                tests_passed += 1
            else:
                print(f"  ❌ Database test failed: {message}")
        except Exception as e:
            print(f"  ❌ Database test failed: {e}")
        
        success_rate = tests_passed / total_tests
        print(f"\n📊 Smoke tests: {tests_passed}/{total_tests} passed ({success_rate:.1%})")
        
        return success_rate >= 0.8  # 80% pass rate required

def main():
    """Main health check function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Surveillance System Health Check")
    parser.add_argument("--wait", action="store_true", help="Wait for system to be ready")
    parser.add_argument("--max-wait", type=int, default=300, help="Maximum wait time in seconds")
    parser.add_argument("--smoke-tests", action="store_true", help="Run smoke tests")
    parser.add_argument("--exit-code", action="store_true", help="Exit with non-zero code if unhealthy")
    args = parser.parse_args()
    
    checker = HealthChecker()
    
    if args.wait:
        ready = checker.wait_for_readiness(max_wait=args.max_wait)
        if not ready and args.exit_code:
            sys.exit(1)
    
    results = checker.run_full_health_check()
    
    if args.smoke_tests:
        smoke_passed = checker.run_smoke_tests()
        if not smoke_passed and args.exit_code:
            sys.exit(1)
    
    if args.exit_code and not results["summary"]["overall_healthy"]:
        sys.exit(1)

if __name__ == "__main__":
    main()