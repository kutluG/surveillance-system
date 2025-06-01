"""
System monitoring script for surveillance infrastructure.
"""
import psutil
import docker
import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any

class SystemMonitor:
    """Monitor system resources and service health."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.services = {
            "edge_service": "http://localhost:8001",
            "mqtt_kafka_bridge": "http://localhost:8002",
            "ingest_service": "http://localhost:8003",
            "rag_service": "http://localhost:8004",
            "prompt_service": "http://localhost:8005",
            "rulegen_service": "http://localhost:8006",
            "notifier": "http://localhost:8007",
            "vms_service": "http://localhost:8008",
        }
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "network": self._get_network_stats()
        }
    
    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    def get_docker_metrics(self) -> List[Dict[str, Any]]:
        """Get Docker container metrics."""
        containers = []
        
        try:
            for container in self.docker_client.containers.list():
                stats = container.stats(stream=False)
                
                # Calculate CPU percentage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                cpu_percent = 0
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
                
                # Memory usage
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100
                
                containers.append({
                    "name": container.name,
                    "id": container.short_id,
                    "status": container.status,
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_usage": memory_usage,
                    "memory_limit": memory_limit,
                    "memory_percent": round(memory_percent, 2),
                    "network_rx": stats['networks']['eth0']['rx_bytes'] if 'networks' in stats and 'eth0' in stats['networks'] else 0,
                    "network_tx": stats['networks']['eth0']['tx_bytes'] if 'networks' in stats and 'eth0' in stats['networks'] else 0
                })
                
        except Exception as e:
            print(f"Error getting Docker metrics: {e}")
        
        return containers
    
    def check_service_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all services."""
        health_status = {}
        
        for service_name, base_url in self.services.items():
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}/health", timeout=5)
                response_time = time.time() - start_time
                
                health_status[service_name] = {
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": round(response_time, 3),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        health_status[service_name]["details"] = health_data
                    except:
                        pass
                        
            except requests.exceptions.RequestException as e:
                health_status[service_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return health_status
    
    def get_prometheus_metrics(self) -> Dict[str, Any]:
        """Get metrics from Prometheus."""
        try:
            response = requests.get("http://localhost:9090/api/v1/query", 
                                  params={"query": "up"}, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_metrics": self.get_system_metrics(),
            "docker_metrics": self.get_docker_metrics(),
            "service_health": self.check_service_health(),
            "prometheus_metrics": self.get_prometheus_metrics()
        }
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        # CPU usage alert
        if metrics["system_metrics"]["cpu"]["percent"] > 90:
            alerts.append({
                "severity": "warning",
                "message": f"High CPU usage: {metrics['system_metrics']['cpu']['percent']:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Memory usage alert
        if metrics["system_metrics"]["memory"]["percent"] > 90:
            alerts.append({
                "severity": "warning",
                "message": f"High memory usage: {metrics['system_metrics']['memory']['percent']:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Disk usage alert
        if metrics["system_metrics"]["disk"]["percent"] > 90:
            alerts.append({
                "severity": "warning",
                "message": f"High disk usage: {metrics['system_metrics']['disk']['percent']:.1f}%",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Service health alerts
        for service_name, health in metrics["service_health"].items():
            if not health.get("healthy", False):
                alerts.append({
                    "severity": "critical",
                    "message": f"Service {service_name} is unhealthy",
                    "details": health,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Container resource alerts
        for container in metrics["docker_metrics"]:
            if container["cpu_percent"] > 95:
                alerts.append({
                    "severity": "warning",
                    "message": f"Container {container['name']} high CPU: {container['cpu_percent']:.1f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            if container["memory_percent"] > 95:
                alerts.append({
                    "severity": "warning", 
                    "message": f"Container {container['name']} high memory: {container['memory_percent']:.1f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def run_continuous_monitoring(self, interval: int = 60):
        """Run continuous monitoring with specified interval."""
        print(f"🔍 Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                print(f"\n📊 Monitoring check at {datetime.utcnow().isoformat()}")
                
                # Get metrics
                metrics = self.generate_monitoring_report()
                
                # Check for alerts
                alerts = self.check_alerts(metrics)
                
                # Display summary
                print(f"CPU: {metrics['system_metrics']['cpu']['percent']:.1f}% | " +
                      f"Memory: {metrics['system_metrics']['memory']['percent']:.1f}% | " +
                      f"Disk: {metrics['system_metrics']['disk']['percent']:.1f}%")
                
                healthy_services = sum(1 for h in metrics['service_health'].values() if h.get('healthy', False))
                total_services = len(metrics['service_health'])
                print(f"Services: {healthy_services}/{total_services} healthy")
                
                # Show alerts
                if alerts:
                    print(f"🚨 {len(alerts)} alerts:")
                    for alert in alerts:
                        print(f"  [{alert['severity'].upper()}] {alert['message']}")
                else:
                    print("✅ No alerts")
                
                # Save metrics to file
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                with open(f"monitoring_{timestamp}.json", 'w') as f:
                    json.dump(metrics, f, indent=2, default=str)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")

def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Surveillance System Monitor")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    if args.once:
        print("📊 Running single monitoring check...")
        metrics = monitor.generate_monitoring_report()
        alerts = monitor.check_alerts(metrics)
        
        print(json.dumps(metrics, indent=2, default=str))
        
        if alerts:
            print(f"\n🚨 {len(alerts)} alerts found:")
            for alert in alerts:
                print(f"  [{alert['severity'].upper()}] {alert['message']}")
    else:
        monitor.run_continuous_monitoring(args.interval)

if __name__ == "__main__":
    main()