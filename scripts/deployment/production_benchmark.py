#!/usr/bin/env python3
"""
Production performance benchmark and optimization suite.
Comprehensive testing for production deployment validation.
"""

import asyncio
import time
import statistics
import psutil
import aiohttp
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Benchmark test result container."""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str]
    memory_usage_mb: float
    cpu_usage_percent: float
    network_io_mb: float
    recommendations: List[str]

class ProductionBenchmark:
    """Production-grade performance benchmarking suite."""
    
    def __init__(self, base_urls: Dict[str, str], config: Dict[str, Any] = None):
        self.base_urls = base_urls
        self.config = config or self._get_default_config()
        self.results: List[BenchmarkResult] = []
        self.start_time = datetime.now()
        
        # Performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024
        self.initial_cpu = psutil.cpu_percent()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default benchmark configuration."""
        return {
            'load_test': {
                'concurrent_users': [10, 25, 50, 100],
                'duration_seconds': 60,
                'ramp_up_seconds': 10
            },
            'stress_test': {
                'max_users': 200,
                'step_size': 25,
                'step_duration': 30
            },
            'endurance_test': {
                'concurrent_users': 20,
                'duration_hours': 1  # Reduced for CI/CD
            },
            'spike_test': {
                'baseline_users': 10,
                'spike_users': 100,
                'spike_duration': 30
            },
            'thresholds': {
                'max_response_time': 2.0,
                'min_success_rate': 0.95,
                'max_error_rate': 0.05,
                'max_memory_mb': 512,
                'max_cpu_percent': 80
            }
        }
    
    async def _make_request(self, session: aiohttp.ClientSession, 
                          endpoint: str, method: str = "GET", 
                          payload: Dict = None) -> Dict[str, Any]:
        """Make a single HTTP request with timing."""
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with session.get(endpoint, timeout=10) as response:
                    await response.text()
                    return {
                        'success': True,
                        'response_time': time.time() - start_time,
                        'status_code': response.status,
                        'error': None
                    }
            elif method.upper() == "POST":
                async with session.post(endpoint, json=payload, timeout=10) as response:
                    await response.text()
                    return {
                        'success': True,
                        'response_time': time.time() - start_time,
                        'status_code': response.status,
                        'error': None
                    }
        except Exception as e:
            return {
                'success': False,
                'response_time': time.time() - start_time,
                'status_code': 0,
                'error': str(e)
            }
    
    async def _user_simulation(self, session: aiohttp.ClientSession,
                             endpoint: str, method: str, payload: Dict,
                             duration: int) -> List[Dict]:
        """Simulate a single user for specified duration."""
        results = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            result = await self._make_request(session, endpoint, method, payload)
            results.append(result)
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        return results
    
    def _calculate_statistics(self, response_times: List[float]) -> Dict[str, float]:
        """Calculate response time statistics."""
        if not response_times:
            return {
                'avg': 0, 'min': 0, 'max': 0,
                'p50': 0, 'p95': 0, 'p99': 0
            }
        
        response_times_sorted = sorted(response_times)
        return {
            'avg': statistics.mean(response_times),
            'min': min(response_times),
            'max': max(response_times),
            'p50': np.percentile(response_times_sorted, 50),
            'p95': np.percentile(response_times_sorted, 95),
            'p99': np.percentile(response_times_sorted, 99)
        }
    
    def _generate_recommendations(self, result: BenchmarkResult) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        thresholds = self.config['thresholds']
        
        if result.success_rate < thresholds['min_success_rate']:
            recommendations.append(f"Low success rate ({result.success_rate:.2%}). Check error logs and server capacity.")
        
        if result.p95_response_time > thresholds['max_response_time']:
            recommendations.append(f"High P95 response time ({result.p95_response_time:.3f}s). Consider caching or optimization.")
        
        if result.memory_usage_mb > thresholds['max_memory_mb']:
            recommendations.append(f"High memory usage ({result.memory_usage_mb:.2f}MB). Check for memory leaks.")
        
        if result.cpu_usage_percent > thresholds['max_cpu_percent']:
            recommendations.append(f"High CPU usage ({result.cpu_usage_percent:.1f}%). Consider scaling or optimization.")
        
        if result.requests_per_second < 10:
            recommendations.append("Low throughput. Check server configuration and network connectivity.")
        
        return recommendations
    
    async def run_load_test(self, test_name: str, endpoint: str, 
                          concurrent_users: int, duration: int,
                          method: str = "GET", payload: Dict = None) -> BenchmarkResult:
        """Run load test with specified parameters."""
        logger.info(f"🔥 Starting load test: {test_name}")
        logger.info(f"   Endpoint: {endpoint}")
        logger.info(f"   Users: {concurrent_users}, Duration: {duration}s")
        
        start_time = datetime.now()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        
        all_results = []
        errors = []
        
        async with aiohttp.ClientSession() as session:
            # Create user simulation tasks
            tasks = []
            for _ in range(concurrent_users):
                task = asyncio.create_task(
                    self._user_simulation(session, endpoint, method, payload, duration)
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            user_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for user_result in user_results:
                if isinstance(user_result, Exception):
                    errors.append(str(user_result))
                else:
                    all_results.extend(user_result)
        
        # Calculate metrics
        end_time = datetime.now()
        test_duration = (end_time - start_time).total_seconds()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_usage = psutil.cpu_percent(interval=1)
        
        successful_results = [r for r in all_results if r['success']]
        failed_results = [r for r in all_results if not r['success']]
        response_times = [r['response_time'] for r in successful_results]
        
        # Calculate statistics
        stats = self._calculate_statistics(response_times)
        
        # Create result object
        result = BenchmarkResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration=test_duration,
            total_requests=len(all_results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            success_rate=len(successful_results) / len(all_results) if all_results else 0,
            avg_response_time=stats['avg'],
            min_response_time=stats['min'],
            max_response_time=stats['max'],
            p50_response_time=stats['p50'],
            p95_response_time=stats['p95'],
            p99_response_time=stats['p99'],
            requests_per_second=len(all_results) / test_duration if test_duration > 0 else 0,
            errors=[r['error'] for r in failed_results if r['error']] + errors,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=cpu_usage,
            network_io_mb=0,  # Would need more complex monitoring
            recommendations=[]
        )
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        logger.info(f"✅ Test completed: {test_name}")
        logger.info(f"   Success Rate: {result.success_rate:.2%}")
        logger.info(f"   Avg Response: {result.avg_response_time:.3f}s")
        logger.info(f"   P95 Response: {result.p95_response_time:.3f}s")
        logger.info(f"   Throughput: {result.requests_per_second:.2f} RPS")
        
        return result
    
    async def run_comprehensive_benchmark(self) -> List[BenchmarkResult]:
        """Run comprehensive benchmark suite."""
        logger.info("🚀 Starting comprehensive production benchmark")
        
        test_scenarios = []
        
        # Health check tests
        for service_name, base_url in self.base_urls.items():
            test_scenarios.append({
                'name': f"{service_name}_health_check",
                'endpoint': f"{base_url}/health",
                'concurrent_users': 50,
                'duration': 30,
                'method': 'GET'
            })
        
        # API endpoint tests
        api_tests = [
            {
                'name': 'rag_analysis_load',
                'endpoint': f"{self.base_urls.get('rag', 'http://localhost:8004')}/analysis",
                'concurrent_users': 20,
                'duration': 60,
                'method': 'POST',
                'payload': {'query': 'test query', 'contexts': []}
            },
            {
                'name': 'prompt_query_load',
                'endpoint': f"{self.base_urls.get('prompt', 'http://localhost:8005')}/query",
                'concurrent_users': 15,
                'duration': 60,
                'method': 'POST',
                'payload': {'query': 'show recent detections', 'limit': 10}
            }
        ]
        test_scenarios.extend(api_tests)
        
        # Run all tests
        results = []
        for scenario in test_scenarios:
            try:
                result = await self.run_load_test(**scenario)
                results.append(result)
                self.results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Test failed: {scenario['name']} - {e}")
        
        return results
    
    async def run_stress_test(self, endpoint: str) -> List[BenchmarkResult]:
        """Run stress test with increasing load."""
        logger.info(f"⚡ Starting stress test: {endpoint}")
        
        config = self.config['stress_test']
        results = []
        
        for users in range(config['step_size'], config['max_users'] + 1, config['step_size']):
            test_name = f"stress_test_{users}_users"
            
            result = await self.run_load_test(
                test_name=test_name,
                endpoint=endpoint,
                concurrent_users=users,
                duration=config['step_duration']
            )
            
            results.append(result)
            self.results.append(result)
            
            # Stop if error rate becomes too high
            if result.success_rate < 0.5:
                logger.warning(f"⚠️ High error rate detected at {users} users, stopping stress test")
                break
            
            # Brief pause between stress levels
            await asyncio.sleep(10)
        
        return results
    
    def generate_html_report(self, output_file: str = "production_benchmark_report.html"):
        """Generate comprehensive HTML report."""
        html_content = self._create_html_report()
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"📊 Report generated: {output_file}")
    
    def _create_html_report(self) -> str:
        """Create HTML report content."""
        if not self.results:
            return "<html><body><h1>No benchmark results available</h1></body></html>"
        
        # Calculate overall statistics
        avg_success_rate = statistics.mean([r.success_rate for r in self.results])
        avg_response_time = statistics.mean([r.avg_response_time for r in self.results])
        total_requests = sum([r.total_requests for r in self.results])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Production Benchmark Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 20px; border-radius: 10px; }}
                .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 10px; 
                           box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; background: white; 
                        border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .success {{ color: #28a745; font-weight: bold; }}
                .warning {{ color: #ffc107; font-weight: bold; }}
                .error {{ color: #dc3545; font-weight: bold; }}
                .metric {{ display: inline-block; margin: 10px; padding: 20px; background: white; 
                         border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .recommendations {{ background: #fff3cd; padding: 15px; border-radius: 10px; 
                                  border-left: 4px solid #ffc107; margin: 20px 0; }}
                .chart-placeholder {{ background: white; padding: 20px; margin: 20px 0; 
                                    border-radius: 10px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔥 Production Benchmark Report</h1>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Test Duration:</strong> {(datetime.now() - self.start_time).total_seconds():.0f} seconds</p>
            </div>
            
            <div class="summary">
                <h2>📊 Overall Summary</h2>
                <div class="metric">
                    <h3>Success Rate</h3>
                    <div class="{'success' if avg_success_rate > 0.95 else 'warning' if avg_success_rate > 0.8 else 'error'}">
                        {avg_success_rate:.2%}
                    </div>
                </div>
                <div class="metric">
                    <h3>Avg Response Time</h3>
                    <div class="{'success' if avg_response_time < 1.0 else 'warning' if avg_response_time < 2.0 else 'error'}">
                        {avg_response_time:.3f}s
                    </div>
                </div>
                <div class="metric">
                    <h3>Total Requests</h3>
                    <div>{total_requests:,}</div>
                </div>
            </div>
            
            <h2>📈 Detailed Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Duration (s)</th>
                    <th>Success Rate</th>
                    <th>Avg Response (s)</th>
                    <th>P95 Response (s)</th>
                    <th>RPS</th>
                    <th>Memory (MB)</th>
                    <th>CPU (%)</th>
                </tr>
        """
        
        for result in self.results:
            success_class = "success" if result.success_rate > 0.95 else "warning" if result.success_rate > 0.8 else "error"
            
            html += f"""
                <tr>
                    <td>{result.test_name}</td>
                    <td>{result.duration:.1f}</td>
                    <td class="{success_class}">{result.success_rate:.2%}</td>
                    <td>{result.avg_response_time:.3f}</td>
                    <td>{result.p95_response_time:.3f}</td>
                    <td>{result.requests_per_second:.1f}</td>
                    <td>{result.memory_usage_mb:.1f}</td>
                    <td>{result.cpu_usage_percent:.1f}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <div class="chart-placeholder">
                <h3>📊 Performance Charts</h3>
                <p>Charts would be generated here in a full implementation using Chart.js or similar</p>
            </div>
            
            <h2>💡 Recommendations</h2>
        """
        
        # Aggregate recommendations
        all_recommendations = []
        for result in self.results:
            all_recommendations.extend(result.recommendations)
        
        unique_recommendations = list(set(all_recommendations))
        
        if unique_recommendations:
            html += '<div class="recommendations"><ul>'
            for recommendation in unique_recommendations:
                html += f'<li>{recommendation}</li>'
            html += '</ul></div>'
        else:
            html += '<div class="recommendations"><p>✅ No performance issues detected!</p></div>'
        
        html += """
            </body>
        </html>
        """
        
        return html
    
    def export_results_csv(self, filename: str = "benchmark_results.csv"):
        """Export results to CSV for analysis."""
        if not self.results:
            logger.warning("No results to export")
            return
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'test_name', 'start_time', 'duration', 'total_requests',
                'successful_requests', 'success_rate', 'avg_response_time',
                'p95_response_time', 'requests_per_second', 'memory_usage_mb',
                'cpu_usage_percent'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                row = {field: getattr(result, field) for field in fieldnames}
                row['start_time'] = result.start_time.isoformat()
                writer.writerow(row)
        
        logger.info(f"📄 Results exported to: {filename}")


async def run_production_validation():
    """Run complete production validation benchmark."""
    services = {
        "edge": "http://localhost:8001",
        "rag": "http://localhost:8004", 
        "prompt": "http://localhost:8005",
        "notifier": "http://localhost:8007"
    }
    
    # Check if services are running
    logger.info("🔍 Checking service availability...")
    available_services = {}
    
    async with aiohttp.ClientSession() as session:
        for name, url in services.items():
            try:
                async with session.get(f"{url}/health", timeout=5) as response:
                    if response.status == 200:
                        available_services[name] = url
                        logger.info(f"✅ {name} service is available")
                    else:
                        logger.warning(f"⚠️ {name} service returned status {response.status}")
            except Exception as e:
                logger.warning(f"❌ {name} service not available: {e}")
    
    if not available_services:
        logger.error("❌ No services available for testing")
        return False
    
    # Run benchmarks
    benchmark = ProductionBenchmark(available_services)
    
    logger.info("🚀 Starting production validation benchmark...")
    results = await benchmark.run_comprehensive_benchmark()
    
    # Run stress test on primary service
    if 'edge' in available_services:
        logger.info("⚡ Running stress test on edge service...")
        stress_results = await benchmark.run_stress_test(f"{available_services['edge']}/health")
    
    # Generate reports
    benchmark.generate_html_report()
    benchmark.export_results_csv()
    
    # Validate results against production thresholds
    passed_tests = 0
    total_tests = len(results)
    
    logger.info("\n📊 Production Validation Results:")
    logger.info("=" * 50)
    
    for result in results:
        status = "✅ PASS" if result.success_rate >= 0.95 and result.p95_response_time <= 2.0 else "❌ FAIL"
        if "PASS" in status:
            passed_tests += 1
        
        logger.info(f"{status} {result.test_name}")
        logger.info(f"    Success Rate: {result.success_rate:.2%}")
        logger.info(f"    P95 Response: {result.p95_response_time:.3f}s")
        logger.info(f"    Throughput: {result.requests_per_second:.1f} RPS")
        
        if result.recommendations:
            logger.info(f"    Recommendations: {'; '.join(result.recommendations)}")
        logger.info("")
    
    success_rate = passed_tests / total_tests
    logger.info(f"🎯 Overall validation: {passed_tests}/{total_tests} tests passed ({success_rate:.1%})")
    
    if success_rate >= 0.8:
        logger.info("🎉 Production validation PASSED!")
        return True
    else:
        logger.error("❌ Production validation FAILED!")
        return False


if __name__ == "__main__":
    import sys
    
    # Run production validation
    success = asyncio.run(run_production_validation())
    sys.exit(0 if success else 1)
