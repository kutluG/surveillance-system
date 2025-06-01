"""
Performance benchmarking suite for the surveillance system.
"""
import time
import asyncio
import statistics
import json
from datetime import datetime
from typing import Dict, List, Any
import aiohttp
import matplotlib.pyplot as plt

class PerformanceBenchmark:
    """Performance benchmarking utility."""
    
    def __init__(self):
        self.results = {}
        self.services = {
            "edge": "http://localhost:8001",
            "bridge": "http://localhost:8002",
            "ingest": "http://localhost:8003",
            "rag": "http://localhost:8004",
            "prompt": "http://localhost:8005",
            "rulegen": "http://localhost:8006",
            "notifier": "http://localhost:8007",
            "vms": "http://localhost:8008",
        }
    
    async def benchmark_endpoint(self, url: str, requests_per_second: int, duration_seconds: int) -> Dict[str, Any]:
        """Benchmark a specific endpoint with controlled load."""
        request_interval = 1.0 / requests_per_second
        end_time = time.time() + duration_seconds
        results = []
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                start = time.time()
                
                try:
                    async with session.get(url, timeout=10) as response:
                        response_time = time.time() - start
                        results.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "response_time": response_time,
                            "status_code": response.status,
                            "success": 200 <= response.status < 300
                        })
                except Exception as e:
                    results.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "response_time": time.time() - start,
                        "status_code": 0,
                        "success": False,
                        "error": str(e)
                    })
                
                # Wait for next request
                elapsed = time.time() - start
                if elapsed < request_interval:
                    await asyncio.sleep(request_interval - elapsed)
        
        return self._analyze_results(results)
    
    def _analyze_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze benchmark results."""
        successful = [r for r in results if r["success"]]
        
        if not successful:
            return {
                "total_requests": len(results),
                "successful_requests": 0,
                "success_rate": 0,
                "error_rate": 1.0,
                "errors": [r.get("error", "Unknown") for r in results if not r["success"]]
            }
        
        response_times = [r["response_time"] for r in successful]
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "success_rate": len(successful) / len(results),
            "error_rate": (len(results) - len(successful)) / len(results),
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
            "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times),
            "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "requests_per_second": len(successful) / (max([r["timestamp"] for r in successful]) - min([r["timestamp"] for r in successful])) if len(successful) > 1 else 0
        }
    
    async def run_service_benchmarks(self, rps: int = 10, duration: int = 60):
        """Run benchmarks for all services."""
        print(f"🏃 Running performance benchmarks ({rps} RPS for {duration}s)")
        print("=" * 60)
        
        for service_name, base_url in self.services.items():
            print(f"\n📊 Benchmarking {service_name.upper()} service...")
            
            health_url = f"{base_url}/health"
            results = await self.benchmark_endpoint(health_url, rps, duration)
            
            self.results[service_name] = results
            
            print(f"  Success Rate: {results['success_rate']:.2%}")
            print(f"  Avg Response: {results['avg_response_time']:.3f}s")
            print(f"  P95 Response: {results['p95_response_time']:.3f}s")
            print(f"  Throughput: {results.get('requests_per_second', 0):.1f} RPS")
    
    def generate_report(self) -> str:
        """Generate performance benchmark report."""
        report = []
        report.append("# Performance Benchmark Report")
        report.append(f"Generated: {datetime.utcnow().isoformat()}Z")
        report.append("")
        
        # Summary table
        report.append("## Summary")
        report.append("| Service | Success Rate | Avg Response | P95 Response | Throughput |")
        report.append("|---------|--------------|--------------|--------------|------------|")
        
        for service_name, results in self.results.items():
            report.append(
                f"| {service_name} | {results['success_rate']:.1%} | "
                f"{results['avg_response_time']:.3f}s | {results['p95_response_time']:.3f}s | "
                f"{results.get('requests_per_second', 0):.1f} RPS |"
            )
        
        # Detailed results
        report.append("\n## Detailed Results")
        for service_name, results in self.results.items():
            report.append(f"\n### {service_name.upper()} Service")
            report.append(f"- Total Requests: {results['total_requests']}")
            report.append(f"- Successful Requests: {results['successful_requests']}")
            report.append(f"- Success Rate: {results['success_rate']:.2%}")
            report.append(f"- Average Response Time: {results['avg_response_time']:.3f}s")
            report.append(f"- Median Response Time: {results['median_response_time']:.3f}s")
            report.append(f"- 95th Percentile: {results['p95_response_time']:.3f}s")
            report.append(f"- 99th Percentile: {results['p99_response_time']:.3f}s")
            report.append(f"- Standard Deviation: {results['std_dev']:.3f}s")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file."""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📁 Results saved to {filename}")
    
    def create_visualizations(self):
        """Create performance visualization charts."""
        if not self.results:
            return
        
        # Response time comparison
        services = list(self.results.keys())
        avg_times = [self.results[s]['avg_response_time'] for s in services]
        p95_times = [self.results[s]['p95_response_time'] for s in services]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Response times
        x_pos = range(len(services))
        ax1.bar([x - 0.2 for x in x_pos], avg_times, 0.4, label='Average', alpha=0.8)
        ax1.bar([x + 0.2 for x in x_pos], p95_times, 0.4, label='95th Percentile', alpha=0.8)
        ax1.set_xlabel('Services')
        ax1.set_ylabel('Response Time (seconds)')
        ax1.set_title('Response Time Comparison')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(services, rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Success rates
        success_rates = [self.results[s]['success_rate'] * 100 for s in services]
        ax2.bar(services, success_rates, alpha=0.8, color='green')
        ax2.set_xlabel('Services')
        ax2.set_ylabel('Success Rate (%)')
        ax2.set_title('Success Rate by Service')
        ax2.set_ylim(0, 105)
        plt.setp(ax2.get_xticklabels(), rotation=45)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        plt.savefig(f"benchmark_charts_{timestamp}.png", dpi=300, bbox_inches='tight')
        print(f"📊 Charts saved to benchmark_charts_{timestamp}.png")

async def main():
    """Run performance benchmarks."""
    benchmark = PerformanceBenchmark()
    
    # Run benchmarks
    await benchmark.run_service_benchmarks(rps=20, duration=30)
    
    # Generate report
    report = benchmark.generate_report()
    print("\n" + "="*60)
    print(report)
    
    # Save results
    benchmark.save_results()
    benchmark.create_visualizations()

if __name__ == "__main__":
    asyncio.run(main())