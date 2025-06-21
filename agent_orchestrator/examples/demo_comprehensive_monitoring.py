"""
Comprehensive Monitoring System Demo

This demo showcases:
- Advanced SLO tracking and alerting
- Real-time anomaly detection
- OpenTelemetry distributed tracing
- Performance dashboard data
- System health monitoring
"""

import asyncio
import time
import random
import json
from datetime import datetime
from typing import List, Dict, Any

from agent_orchestrator.comprehensive_monitoring import (
    ComprehensiveMonitor,
    initialize_monitoring,
    SLODefinition,
    AnomalyDetection,
    SLOType,
    AnomalyType,
    AlertSeverity
)


class MonitoringDemo:
    """Demonstration of comprehensive monitoring capabilities"""
    
    def __init__(self):
        self.monitor = initialize_monitoring(enable_opentelemetry=False)
        self.demo_running = False
        
    async def run_complete_demo(self):
        """Run complete monitoring demonstration"""
        print("🚀 Starting Comprehensive Monitoring Demo")
        print("=" * 60)
        
        # Run different demo scenarios
        await self.demo_slo_tracking()
        await self.demo_anomaly_detection()
        await self.demo_performance_monitoring()
        await self.demo_dashboard_data()
        await self.demo_health_monitoring()
        
        print("\n✅ Demo completed successfully!")
        
    async def demo_slo_tracking(self):
        """Demonstrate SLO tracking capabilities"""
        print("\n📊 SLO Tracking Demo")
        print("-" * 30)
        
        # Show default SLOs
        slo_status = self.monitor.slo_tracker.get_all_slo_status()
        print(f"📋 Default SLOs configured: {len(slo_status)}")
        
        for name, status in slo_status.items():
            print(f"  • {name}: {status.definition.type.value} "
                  f"(target: {status.definition.target})")
        
        # Add custom SLO
        custom_slo = SLODefinition(
            name="custom_response_time",
            type=SLOType.LATENCY,
            target=1.5,  # 1.5 second threshold
            window=300,  # 5 minutes
            alerting_threshold=90.0,  # 90% of requests under 1.5s
            description="Custom response time SLO"
        )
        
        self.monitor.slo_tracker.add_slo(custom_slo)
        print(f"➕ Added custom SLO: {custom_slo.name}")
        
        # Simulate requests to test SLO
        print("🔄 Simulating requests for SLO testing...")
        
        success_count = 0
        total_requests = 50
        
        for i in range(total_requests):
            # Generate realistic latency with some variation
            base_latency = 0.8
            variation = random.uniform(-0.3, 0.7)
            latency = max(0.1, base_latency + variation)
            
            # Occasionally generate slow requests
            if random.random() < 0.1:  # 10% chance of slow request
                latency += random.uniform(1.0, 3.0)
            
            success = random.random() > 0.02  # 98% success rate
            if success:
                success_count += 1
                
            await self.monitor.record_orchestration_metrics(
                latency=latency,
                success=success,
                agent_type="demo_agent",
                task_type="demo_task"
            )
            
            # Update custom SLO
            self.monitor.slo_tracker.update_slo_metric("custom_response_time", latency)
            
            if i % 10 == 0:
                print(f"  Processed {i + 1}/{total_requests} requests...")
            
            await asyncio.sleep(0.05)  # Small delay
        
        # Show SLO results
        print(f"\n📈 SLO Results after {total_requests} requests:")
        updated_status = self.monitor.slo_tracker.get_all_slo_status()
        
        for name, status in updated_status.items():
            health_icon = "✅" if status.is_healthy else "❌"
            print(f"  {health_icon} {name}: {status.current_value:.1f} "
                  f"(target: {status.definition.target})")
            if status.breach_count > 0:
                print(f"    ⚠️  Breaches: {status.breach_count}")
        
    async def demo_anomaly_detection(self):
        """Demonstrate anomaly detection capabilities"""
        print("\n🔍 Anomaly Detection Demo")
        print("-" * 30)
        
        # Add custom anomaly detection
        latency_config = AnomalyDetection(
            metric_name="demo_latency_spikes",
            detection_type=AnomalyType.LATENCY_SPIKE,
            threshold_multiplier=2.0,
            window_size=20,
            cooldown_period=10
        )
        
        self.monitor.anomaly_detector.add_detection_config(latency_config)
        print("🎛️  Configured latency spike detection")
        
        # Generate normal traffic
        print("📊 Generating baseline traffic...")
        normal_latency = 1.0
        
        for i in range(20):
            latency = normal_latency + random.uniform(-0.2, 0.2)
            anomaly = self.monitor.anomaly_detector.add_metric_value(
                "demo_latency_spikes", latency
            )
            if anomaly:
                print(f"🚨 Unexpected anomaly during baseline: {anomaly.description}")
            await asyncio.sleep(0.02)
        
        print("✅ Baseline established")
        
        # Generate anomalous traffic
        print("⚡ Generating anomalous traffic...")
        
        # Generate some normal requests
        for i in range(5):
            latency = normal_latency + random.uniform(-0.1, 0.1)
            self.monitor.anomaly_detector.add_metric_value("demo_latency_spikes", latency)
            await asyncio.sleep(0.02)
        
        # Generate spike
        spike_latency = normal_latency * 5  # 5x normal latency
        print(f"🔥 Generating latency spike: {spike_latency:.2f}s")
        
        anomaly = self.monitor.anomaly_detector.add_metric_value(
            "demo_latency_spikes", spike_latency
        )
        
        if anomaly:
            print(f"🚨 ANOMALY DETECTED!")
            print(f"   Type: {anomaly.detection.detection_type.value}")
            print(f"   Severity: {anomaly.severity.value}")
            print(f"   Value: {anomaly.value:.2f}s vs baseline {anomaly.baseline:.2f}s")
            print(f"   Description: {anomaly.description}")
        else:
            print("❌ Anomaly detection failed - check configuration")
        
        # Test cooldown period
        print("❄️  Testing cooldown period...")
        immediate_anomaly = self.monitor.anomaly_detector.add_metric_value(
            "demo_latency_spikes", spike_latency
        )
        
        if immediate_anomaly:
            print("❌ Cooldown period not working")
        else:
            print("✅ Cooldown period working correctly")
    
    async def demo_performance_monitoring(self):
        """Demonstrate performance monitoring"""
        print("\n⚡ Performance Monitoring Demo")
        print("-" * 35)
        
        # Simulate different agent types with varying performance
        agent_scenarios = {
            "fast_agent": {"base_latency": 0.5, "error_rate": 0.01},
            "slow_agent": {"base_latency": 2.0, "error_rate": 0.03},
            "unreliable_agent": {"base_latency": 1.0, "error_rate": 0.10},
        }
        
        print(f"🤖 Simulating {len(agent_scenarios)} different agent types...")
        
        for agent_type, config in agent_scenarios.items():
            print(f"  Testing {agent_type}...")
            
            for i in range(20):
                # Generate latency with variation
                latency = config["base_latency"] + random.uniform(-0.2, 0.5)
                success = random.random() > config["error_rate"]
                
                await self.monitor.record_orchestration_metrics(
                    latency=latency,
                    success=success,
                    agent_type=agent_type,
                    task_type="performance_test"
                )
                
                await asyncio.sleep(0.01)
        
        # Get performance results
        dashboard_data = self.monitor.get_dashboard_data()
        
        print("\n📊 Performance Results:")
        for agent_type, metrics in dashboard_data.agent_performance_metrics.items():
            print(f"  🤖 {agent_type}:")
            print(f"    ⏱️  Avg Latency: {metrics['avg_latency']:.3f}s")
            print(f"    ✅ Success Rate: {metrics['success_rate']:.1f}%")
            print(f"    📊 Total Requests: {metrics['total_requests']}")
            print(f"    ❌ Recent Errors: {metrics['recent_errors']}")
    
    async def demo_dashboard_data(self):
        """Demonstrate dashboard data generation"""
        print("\n📋 Dashboard Data Demo")
        print("-" * 25)
        
        # Generate some activity
        print("📊 Generating dashboard activity...")
        
        for i in range(30):
            agent_type = random.choice(["web_agent", "api_agent", "batch_agent"])
            task_type = random.choice(["query", "update", "report"])
            
            latency = random.uniform(0.5, 3.0)
            success = random.random() > 0.05
            
            await self.monitor.record_orchestration_metrics(
                latency=latency,
                success=success,
                agent_type=agent_type,
                task_type=task_type
            )
            
            await asyncio.sleep(0.02)
        
        # Get dashboard data
        dashboard_data = self.monitor.get_dashboard_data()
        
        print("📊 Dashboard Data Generated:")
        print(f"  🕐 Timestamp: {dashboard_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  🤖 Active Agents: {len(dashboard_data.agent_performance_metrics)}")
        print(f"  📈 SLO Metrics: {len(dashboard_data.slo_status)}")
        print(f"  🚨 Anomalies: {len(dashboard_data.anomalies)}")
        print(f"  ⚡ System Status: {dashboard_data.system_health['overall_status']}")
        
        # Show recent latency trends
        print("\n📈 Recent Latency Trends:")
        for agent_type, latencies in dashboard_data.task_latency_by_agent.items():
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                print(f"  🤖 {agent_type}:")
                print(f"    Avg: {avg_latency:.3f}s, Min: {min_latency:.3f}s, Max: {max_latency:.3f}s")
    
    async def demo_health_monitoring(self):
        """Demonstrate system health monitoring"""
        print("\n🏥 Health Monitoring Demo")
        print("-" * 30)
        
        # Get current health status
        health_status = self.monitor.get_health_status()
        
        print("🔍 Current System Health:")
        print(f"  📊 Overall Status: {health_status['status']}")
        print(f"  📈 SLO Health: {health_status['slo_health']}")
        print(f"  🤖 Active Agents: {health_status['active_agents']}")
        print(f"  🔄 OpenTelemetry: {'Enabled' if health_status['opentelemetry_enabled'] else 'Disabled'}")
        print(f"  🕐 Last Check: {health_status['timestamp']}")
        
        # Simulate health degradation
        print("\n⚠️  Simulating system degradation...")
        
        # Generate high error rate
        for i in range(20):
            await self.monitor.record_orchestration_metrics(
                latency=random.uniform(5.0, 10.0),  # High latency
                success=random.random() > 0.5,  # 50% error rate
                agent_type="degraded_agent",
                task_type="stress_test"
            )
            await asyncio.sleep(0.01)
        
        # Check health again
        degraded_health = self.monitor.get_health_status()
        print(f"🚨 Health After Degradation: {degraded_health['status']}")
        
        # Show SLO breaches
        slo_status = self.monitor.slo_tracker.get_all_slo_status()
        breached_slos = [name for name, status in slo_status.items() if not status.is_healthy]
        
        if breached_slos:
            print(f"❌ SLO Breaches: {', '.join(breached_slos)}")
        else:
            print("✅ All SLOs still healthy")
    
    async def demo_real_time_monitoring(self, duration_seconds: int = 30):
        """Demonstrate real-time monitoring"""
        print(f"\n🔄 Real-time Monitoring Demo ({duration_seconds}s)")
        print("-" * 40)
        
        self.demo_running = True
        start_time = time.time()
        
        # Background task to generate traffic
        async def generate_traffic():
            while self.demo_running:
                agent_type = random.choice(["realtime_agent_1", "realtime_agent_2", "realtime_agent_3"])
                
                # Simulate varying load
                base_latency = 1.0
                if random.random() < 0.1:  # 10% chance of spike
                    latency = base_latency * random.uniform(3, 8)
                else:
                    latency = base_latency + random.uniform(-0.3, 0.7)
                
                success = random.random() > 0.02  # 98% success rate
                
                await self.monitor.record_orchestration_metrics(
                    latency=latency,
                    success=success,
                    agent_type=agent_type,
                    task_type="realtime_task"
                )
                
                await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Background task to report status
        async def report_status():
            while self.demo_running:
                dashboard_data = self.monitor.get_dashboard_data()
                elapsed = time.time() - start_time
                
                print(f"\r⏱️  {elapsed:.1f}s | "
                      f"Agents: {len(dashboard_data.agent_performance_metrics)} | "
                      f"Status: {dashboard_data.system_health['overall_status']} | "
                      f"Anomalies: {len(dashboard_data.anomalies)}", end="")
                
                await asyncio.sleep(2)
        
        # Run monitoring tasks
        traffic_task = asyncio.create_task(generate_traffic())
        status_task = asyncio.create_task(report_status())
        
        # Run for specified duration
        await asyncio.sleep(duration_seconds)
        self.demo_running = False
        
        # Clean up tasks
        traffic_task.cancel()
        status_task.cancel()
        
        print(f"\n✅ Real-time monitoring completed")
        
        # Final summary
        final_data = self.monitor.get_dashboard_data()
        print(f"📊 Final Stats:")
        print(f"  Total Agents: {len(final_data.agent_performance_metrics)}")
        for agent_type, metrics in final_data.agent_performance_metrics.items():
            print(f"    {agent_type}: {metrics['total_requests']} requests, "
                  f"{metrics['success_rate']:.1f}% success")
    
    def export_demo_results(self) -> Dict[str, Any]:
        """Export demo results for analysis"""
        dashboard_data = self.monitor.get_dashboard_data()
        health_status = self.monitor.get_health_status()
        
        return {
            "demo_timestamp": datetime.now().isoformat(),
            "system_health": health_status,
            "agent_performance": dashboard_data.agent_performance_metrics,
            "slo_status": {
                name: {
                    "name": status.definition.name,
                    "current_value": status.current_value,
                    "is_healthy": status.is_healthy,
                    "breach_count": status.breach_count
                }
                for name, status in dashboard_data.slo_status.items()
            },
            "total_agents": len(dashboard_data.agent_performance_metrics),
            "opentelemetry_enabled": health_status["opentelemetry_enabled"]
        }


async def main():
    """Main demo function"""
    demo = MonitoringDemo()
    
    try:
        # Run complete demo
        await demo.run_complete_demo()
        
        # Optional: Run real-time demo
        print(f"\n🤔 Would you like to see real-time monitoring? (runs for 30 seconds)")
        print("   This will show live metrics updates...")
        
        # For demo purposes, we'll skip the interactive part
        # and just run a shorter real-time demo
        await demo.demo_real_time_monitoring(10)  # 10 seconds
        
        # Export results
        results = demo.export_demo_results()
        print(f"\n📄 Demo Results Summary:")
        print(json.dumps(results, indent=2))
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎯 Comprehensive Monitoring System Demo")
    print("This demo showcases advanced monitoring capabilities")
    print("including SLO tracking, anomaly detection, and real-time dashboards")
    print()
    
    asyncio.run(main())
