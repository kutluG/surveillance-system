"""
Load testing for the surveillance system.
Tests system performance under various load conditions.
"""
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import pytest

class LoadTester:
    """Load testing utility for surveillance services."""
    
    def __init__(self, base_urls):
        self.base_urls = base_urls
        self.results = []
    
    async def make_request(self, session, url, method="GET", json_data=None):
        """Make an async HTTP request and record timing."""
        start_time = time.time()
        try:
            if method == "GET":
                async with session.get(url, timeout=10) as response:
                    status = response.status
                    await response.text()  # Consume response
            elif method == "POST":
                async with session.post(url, json=json_data, timeout=10) as response:
                    status = response.status
                    await response.text()
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "url": url,
                "status": status,
                "response_time": response_time,
                "success": 200 <= status < 300
            }
        except Exception as e:
            end_time = time.time()
            return {
                "url": url,
                "status": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e)
            }
    
    async def run_concurrent_requests(self, url, num_requests=50, method="GET", json_data=None):
        """Run multiple concurrent requests to a single endpoint."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(num_requests):
                task = self.make_request(session, url, method, json_data)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
    
    def analyze_results(self, results):
        """Analyze load test results."""
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        if successful:
            response_times = [r["response_time"] for r in successful]
            analysis = {
                "total_requests": len(results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": len(successful) / len(results),
                "avg_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times),
            }
        else:
            analysis = {
                "total_requests": len(results),
                "successful_requests": 0,
                "failed_requests": len(failed),
                "success_rate": 0,
                "errors": [r.get("error", "Unknown") for r in failed]
            }
        
        return analysis

@pytest.mark.asyncio
class TestLoad:
    """Load testing suite."""
    
    def setup_method(self):
        """Setup load tester."""
        self.services = {
            "edge": "http://localhost:8001",
            "ingest": "http://localhost:8003",
            "rag": "http://localhost:8004",
            "prompt": "http://localhost:8005",
            "notifier": "http://localhost:8007",
            "vms": "http://localhost:8008",
        }
        self.load_tester = LoadTester(self.services)
    
    async def test_health_endpoint_load(self):
        """Test load on health endpoints."""
        print("\n=== Health Endpoint Load Test ===")
        
        for service_name, base_url in self.services.items():
            url = f"{base_url}/health"
            results = await self.load_tester.run_concurrent_requests(url, num_requests=100)
            analysis = self.load_tester.analyze_results(results)
            
            print(f"\n{service_name.upper()} Service:")
            print(f"  Success Rate: {analysis['success_rate']:.2%}")
            print(f"  Avg Response Time: {analysis.get('avg_response_time', 0):.3f}s")
            print(f"  P95 Response Time: {analysis.get('p95_response_time', 0):.3f}s")
            
            # Assertions
            assert analysis["success_rate"] >= 0.95, f"{service_name} success rate too low"
            assert analysis.get("avg_response_time", 10) < 2.0, f"{service_name} too slow"
    
    async def test_prompt_service_load(self):
        """Test load on prompt service query endpoint."""
        print("\n=== Prompt Service Load Test ===")
        
        query_data = {
            "query": "Show me detection events from today",
            "limit": 5
        }
        
        url = f"{self.services['prompt']}/query"
        results = await self.load_tester.run_concurrent_requests(
            url, num_requests=20, method="POST", json_data=query_data
        )
        analysis = self.load_tester.analyze_results(results)
        
        print(f"Success Rate: {analysis['success_rate']:.2%}")
        print(f"Avg Response Time: {analysis.get('avg_response_time', 0):.3f}s")
        
        assert analysis["success_rate"] >= 0.90
        assert analysis.get("avg_response_time", 10) < 5.0
    
    async def test_notification_load(self):
        """Test load on notification service."""
        print("\n=== Notification Service Load Test ===")
        
        notification_data = {
            "channel": "email",
            "recipients": ["test@example.com"],
            "subject": "Load Test Notification",
            "message": "This is a load test notification"
        }
        
        url = f"{self.services['notifier']}/send"
        results = await self.load_tester.run_concurrent_requests(
            url, num_requests=10, method="POST", json_data=notification_data
        )
        analysis = self.load_tester.analyze_results(results)
        
        print(f"Success Rate: {analysis['success_rate']:.2%}")
        print(f"Avg Response Time: {analysis.get('avg_response_time', 0):.3f}s")
        
        assert analysis["success_rate"] >= 0.90
    
    async def test_mixed_workload(self):
        """Test mixed workload across all services."""
        print("\n=== Mixed Workload Test ===")
        
        tasks = []
        
        # Health checks (lightweight)
        for service_name, base_url in self.services.items():
            url = f"{base_url}/health"
            task = self.load_tester.run_concurrent_requests(url, num_requests=20)
            tasks.append(task)
        
        # Query requests (medium weight)
        query_data = {"query": "test query", "limit": 3}
        task = self.load_tester.run_concurrent_requests(
            f"{self.services['prompt']}/query", 
            num_requests=10, 
            method="POST", 
            json_data=query_data
        )
        tasks.append(task)
        
        # Run all tasks concurrently
        all_results = await asyncio.gather(*tasks)
        
        # Analyze overall performance
        total_requests = sum(len(results) for results in all_results)
        total_successful = sum(
            len([r for r in results if r["success"]]) 
            for results in all_results
        )
        
        overall_success_rate = total_successful / total_requests
        print(f"Overall Success Rate: {overall_success_rate:.2%}")
        print(f"Total Requests: {total_requests}")
        
        assert overall_success_rate >= 0.90

if __name__ == "__main__":
    # Run basic load tests
    import sys
    
    async def run_basic_load_test():
        tester = TestLoad()
        tester.setup_method()
        
        print("Running basic load tests...")
        
        try:
            await tester.test_health_endpoint_load()
            print("\n✓ Health endpoint load test passed")
            
            await tester.test_prompt_service_load()
            print("✓ Prompt service load test passed")
            
            await tester.test_mixed_workload()
            print("✓ Mixed workload test passed")
            
            print("\n🎉 All load tests passed!")
            
        except Exception as e:
            print(f"\n❌ Load test failed: {e}")
            sys.exit(1)
    
    asyncio.run(run_basic_load_test())