"""
Advanced performance testing framework for surveillance system.
Includes benchmarking, stress testing, and performance profiling.
"""
import asyncio
import time
import statistics
import psutil
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


@dataclass
class PerformanceMetrics:
    """Container for performance test results."""
    test_name: str
    duration: float
    success_rate: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    errors: List[str]
    memory_usage_mb: float
    cpu_usage_percent: float


class PerformanceTester:
    """Advanced performance testing framework."""
    
    def __init__(self, base_urls: Dict[str, str]):
        self.base_urls = base_urls
        self.results: List[PerformanceMetrics] = []
        
    async def run_load_test(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
        concurrent_users: int = 10,
        duration_seconds: int = 60,
        ramp_up_seconds: int = 10
    ) -> PerformanceMetrics:
        """Run a comprehensive load test."""
        print(f"\n🔥 Starting load test: {endpoint}")
        print(f"   Users: {concurrent_users}, Duration: {duration_seconds}s")
        
        start_time = time.time()
        results = []
        errors = []
        
        # Monitor system resources
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        async with aiohttp.ClientSession() as session:
            # Gradual ramp-up
            tasks = []
            for i in range(concurrent_users):
                await asyncio.sleep(ramp_up_seconds / concurrent_users)
                task = asyncio.create_task(
                    self._user_session(session, endpoint, method, payload, duration_seconds)
                )
                tasks.append(task)
            
            # Wait for all users to complete
            user_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for user_result in user_results:
                if isinstance(user_result, Exception):
                    errors.append(str(user_result))
                else:
                    results.extend(user_result)
        
        # Calculate metrics
        total_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_usage = psutil.cpu_percent(interval=1)
        
        return self._calculate_metrics(
            test_name=f"Load Test - {endpoint}",
            results=results,
            errors=errors,
            duration=total_time,
            memory_usage=final_memory - initial_memory,
            cpu_usage=cpu_usage
        )
    
    async def _user_session(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        method: str,
        payload: Optional[Dict],
        duration: int
    ) -> List[Dict]:
        """Simulate a single user session."""
        results = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            start = time.time()
            try:
                if method.upper() == "GET":
                    async with session.get(endpoint) as response:
                        await response.text()
                        status = response.status
                elif method.upper() == "POST":
                    async with session.post(endpoint, json=payload) as response:
                        await response.text()
                        status = response.status
                
                response_time = time.time() - start
                results.append({
                    "response_time": response_time,
                    "status": status,
                    "success": 200 <= status < 300
                })
                
            except Exception as e:
                response_time = time.time() - start
                results.append({
                    "response_time": response_time,
                    "status": 0,
                    "success": False,
                    "error": str(e)
                })
            
            # Brief pause between requests
            await asyncio.sleep(0.1)
        
        return results
    
    async def run_stress_test(
        self,
        endpoint: str,
        max_users: int = 100,
        step_size: int = 10,
        step_duration: int = 30
    ) -> List[PerformanceMetrics]:
        """Run a stress test with gradually increasing load."""
        print(f"\n⚡ Starting stress test: {endpoint}")
        stress_results = []
        
        for users in range(step_size, max_users + 1, step_size):
            print(f"   Testing with {users} concurrent users...")
            
            result = await self.run_load_test(
                endpoint=endpoint,
                concurrent_users=users,
                duration_seconds=step_duration,
                ramp_up_seconds=5
            )
            
            stress_results.append(result)
            
            # Stop if error rate becomes too high
            if result.success_rate < 0.5:
                print(f"   ⚠️  High error rate detected, stopping stress test")
                break
        
        return stress_results
    
    async def run_spike_test(
        self,
        endpoint: str,
        baseline_users: int = 10,
        spike_users: int = 100,
        spike_duration: int = 30
    ) -> Dict[str, PerformanceMetrics]:
        """Test system behavior under sudden load spikes."""
        print(f"\n📈 Starting spike test: {endpoint}")
        
        # Baseline load
        print("   Running baseline load...")
        baseline = await self.run_load_test(
            endpoint=endpoint,
            concurrent_users=baseline_users,
            duration_seconds=60
        )
        
        # Spike load
        print(f"   Applying spike load ({spike_users} users)...")
        spike = await self.run_load_test(
            endpoint=endpoint,
            concurrent_users=spike_users,
            duration_seconds=spike_duration,
            ramp_up_seconds=5
        )
        
        # Recovery
        print("   Testing recovery...")
        recovery = await self.run_load_test(
            endpoint=endpoint,
            concurrent_users=baseline_users,
            duration_seconds=60
        )
        
        return {
            "baseline": baseline,
            "spike": spike,
            "recovery": recovery
        }
    
    async def run_endurance_test(
        self,
        endpoint: str,
        concurrent_users: int = 20,
        duration_hours: int = 2
    ) -> PerformanceMetrics:
        """Run a long-duration endurance test."""
        print(f"\n⏰ Starting {duration_hours}h endurance test: {endpoint}")
        
        duration_seconds = duration_hours * 3600
        return await self.run_load_test(
            endpoint=endpoint,
            concurrent_users=concurrent_users,
            duration_seconds=duration_seconds,
            ramp_up_seconds=60
        )
    
    def _calculate_metrics(
        self,
        test_name: str,
        results: List[Dict],
        errors: List[str],
        duration: float,
        memory_usage: float,
        cpu_usage: float
    ) -> PerformanceMetrics:
        """Calculate performance metrics from test results."""
        if not results:
            return PerformanceMetrics(
                test_name=test_name,
                duration=duration,
                success_rate=0.0,
                avg_response_time=0.0,
                p50_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                requests_per_second=0.0,
                errors=errors,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage
            )
        
        successful = [r for r in results if r["success"]]
        response_times = [r["response_time"] for r in successful]
        
        if response_times:
            response_times_sorted = sorted(response_times)
            p50 = np.percentile(response_times_sorted, 50)
            p95 = np.percentile(response_times_sorted, 95)
            p99 = np.percentile(response_times_sorted, 99)
        else:
            p50 = p95 = p99 = 0.0
        
        return PerformanceMetrics(
            test_name=test_name,
            duration=duration,
            success_rate=len(successful) / len(results),
            avg_response_time=statistics.mean(response_times) if response_times else 0.0,
            p50_response_time=p50,
            p95_response_time=p95,
            p99_response_time=p99,
            min_response_time=min(response_times) if response_times else 0.0,
            max_response_time=max(response_times) if response_times else 0.0,
            requests_per_second=len(results) / duration,
            errors=errors,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage
        )
    
    def generate_report(self, output_file: str = "performance_report.html"):
        """Generate an HTML performance report."""
        html_content = self._create_html_report()
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"📊 Performance report saved to: {output_file}")
    
    def _create_html_report(self) -> str:
        """Create HTML performance report."""
        if not self.results:
            return "<html><body><h1>No performance test results available</h1></body></html>"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #f2f2f2; }
                .metric { margin: 10px 0; }
                .success { color: green; }
                .warning { color: orange; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>🔥 Performance Test Report</h1>
            <p><strong>Generated:</strong> {timestamp}</p>
            
            <h2>Summary</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Duration (s)</th>
                    <th>Success Rate</th>
                    <th>Avg Response Time (s)</th>
                    <th>P95 Response Time (s)</th>
                    <th>Requests/sec</th>
                    <th>Memory Usage (MB)</th>
                    <th>CPU Usage (%)</th>
                </tr>
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        for result in self.results:
            success_class = "success" if result.success_rate > 0.95 else "warning" if result.success_rate > 0.8 else "error"
            
            html += f"""
                <tr>
                    <td>{result.test_name}</td>
                    <td>{result.duration:.2f}</td>
                    <td class="{success_class}">{result.success_rate:.2%}</td>
                    <td>{result.avg_response_time:.3f}</td>
                    <td>{result.p95_response_time:.3f}</td>
                    <td>{result.requests_per_second:.2f}</td>
                    <td>{result.memory_usage_mb:.2f}</td>
                    <td>{result.cpu_usage_percent:.1f}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        # Add recommendations based on results
        for result in self.results:
            if result.success_rate < 0.95:
                html += f"<li class='error'>⚠️ {result.test_name}: Low success rate ({result.success_rate:.2%})</li>"
            if result.p95_response_time > 2.0:
                html += f"<li class='warning'>🐌 {result.test_name}: High P95 response time ({result.p95_response_time:.3f}s)</li>"
            if result.memory_usage_mb > 500:
                html += f"<li class='warning'>💾 {result.test_name}: High memory usage ({result.memory_usage_mb:.2f}MB)</li>"
        
        html += """
            </ul>
            </body>
        </html>
        """
        
        return html


# Example usage and test scenarios
async def run_comprehensive_performance_tests():
    """Run a comprehensive suite of performance tests."""
    services = {
        "edge": "http://localhost:8001",
        "rag": "http://localhost:8004",
        "prompt": "http://localhost:8005",
        "notifier": "http://localhost:8007",
    }
    
    tester = PerformanceTester(services)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Health Check Load Test",
            "endpoint": f"{services['edge']}/health",
            "method": "GET",
            "concurrent_users": 50,
            "duration": 60
        },
        {
            "name": "RAG Analysis Load Test",
            "endpoint": f"{services['rag']}/analysis",
            "method": "POST",
            "payload": {"query": "test query", "contexts": []},
            "concurrent_users": 20,
            "duration": 120
        },
        {
            "name": "Prompt Service Query Test",
            "endpoint": f"{services['prompt']}/query",
            "method": "POST",
            "payload": {"query": "show recent detections", "limit": 10},
            "concurrent_users": 30,
            "duration": 90
        }
    ]
    
    # Run load tests
    for scenario in test_scenarios:
        result = await tester.run_load_test(**scenario)
        tester.results.append(result)
        print(f"✅ Completed: {scenario['name']}")
        print(f"   Success Rate: {result.success_rate:.2%}")
        print(f"   Avg Response Time: {result.avg_response_time:.3f}s")
        print(f"   P95 Response Time: {result.p95_response_time:.3f}s")
    
    # Run stress test on critical endpoint
    stress_results = await tester.run_stress_test(
        endpoint=f"{services['edge']}/health",
        max_users=200,
        step_size=25,
        step_duration=30
    )
    tester.results.extend(stress_results)
    
    # Generate report
    tester.generate_report("surveillance_performance_report.html")
    print("\n🎉 Performance testing completed!")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_performance_tests())
