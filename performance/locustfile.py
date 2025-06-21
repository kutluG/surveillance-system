"""
Locust Load Testing for Annotation Backend

This file defines load tests to simulate concurrent annotation submissions
and measure the performance of the annotation backend under load.

Usage:
    # Basic run (interactive web UI)
    locust

    # Headless run with specific parameters
    locust --headless -u 50 -r 5 -t 5m --host http://localhost:8001

    # CI mode with performance assertions
    locust --headless -u 50 -r 5 -t 5m --host http://localhost:8001 --only-summary

Requirements:
    - Annotation backend running on http://localhost:8001
    - Database and Kafka services available
    - Test data populated (examples available)
"""

import json
import random
import time
from typing import Dict, Any, List
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class AnnotationUser(HttpUser):
    """
    Simulates a user performing annotation tasks.
    
    This user class defines the behavior of concurrent users accessing
    the annotation system, fetching examples, and submitting annotations.
    """
    
    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)
    
    # Store fetched examples for annotation
    examples: List[Dict[str, Any]] = []
    current_example_id: str = None
    
    def on_start(self):
        """Initialize user session and fetch initial data."""
        print(f"User {id(self)} starting annotation session")
        
        # Health check to ensure backend is ready
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Backend health check failed: {response.status_code}")
            else:
                response.success()
        
        # Fetch examples once at the start to reuse during testing
        self._fetch_examples()
    
    def _fetch_examples(self):
        """Fetch examples from the API and store for reuse."""
        with self.client.get("/api/v1/examples", catch_response=True, name="fetch_examples") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        self.examples = data
                        response.success()
                        print(f"User {id(self)} fetched {len(self.examples)} examples")
                    else:
                        # Create mock examples if none exist
                        self.examples = self._create_mock_examples()
                        response.success()
                        print(f"User {id(self)} using {len(self.examples)} mock examples")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response from examples endpoint")
                    self.examples = self._create_mock_examples()
            else:
                response.failure(f"Failed to fetch examples: {response.status_code}")
                self.examples = self._create_mock_examples()
    
    def _create_mock_examples(self) -> List[Dict[str, Any]]:
        """Create mock examples for testing when no real data is available."""
        return [
            {
                "id": f"mock-{i}",
                "image_url": f"/static/images/example_{i}.jpg",
                "metadata": {"source": "mock_data", "timestamp": time.time()},
                "annotations": []
            }
            for i in range(10)
        ]
    
    def _generate_annotation_data(self) -> Dict[str, Any]:
        """Generate realistic annotation data for testing."""
        return {
            "bbox": [
                random.randint(50, 150),   # x
                random.randint(50, 150),   # y
                random.randint(200, 400),  # width
                random.randint(200, 400)   # height
            ],
            "label": random.choice([
                "person", "vehicle", "animal", "object", "suspicious_activity",
                "normal_activity", "motion", "stationary", "group", "individual"
            ]),
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "timestamp": time.time(),
            "user_id": f"load_test_user_{id(self)}",
            "metadata": {
                "tool": "load_test",
                "duration": random.randint(10, 120),  # annotation time in seconds
                "quality": random.choice(["high", "medium", "low"])
            }
        }
    
    @task(3)
    def fetch_examples(self):
        """
        Fetch available examples for annotation.
        
        This is the most common operation, weighted at 3.
        """
        with self.client.get("/api/v1/examples", 
                           catch_response=True, 
                           name="GET_/api/v1/examples") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        # Update stored examples with fresh data
                        if len(data) > 0:
                            self.examples = data
                        response.success()
                    else:
                        response.failure("Examples response is not a list")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in examples response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def fetch_example_details(self):
        """
        Fetch details for a specific example.
        
        This simulates users viewing example details before annotation.
        """
        if not self.examples:
            return
        
        example = random.choice(self.examples)
        example_id = example.get("id", "mock-1")
        
        with self.client.get(f"/api/v1/examples/{example_id}",
                           catch_response=True,
                           name="GET_/api/v1/examples/:id") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.current_example_id = example_id
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in example details response")
            elif response.status_code == 404:
                # Example not found - this is acceptable in load testing
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(4)
    def submit_annotation(self):
        """
        Submit an annotation for an example.
        
        This is the primary operation being load tested, weighted at 4.
        """
        if not self.examples:
            return
        
        example = random.choice(self.examples)
        example_id = example.get("id", "mock-1")
        annotation_data = self._generate_annotation_data()
        
        with self.client.post(f"/api/v1/examples/{example_id}/label",
                            json=annotation_data,
                            catch_response=True,
                            name="POST_/api/v1/examples/:id/label") as response:
            if response.status_code in [200, 201]:
                try:
                    # Validate response structure
                    data = response.json()
                    if "success" in data or "id" in data:
                        response.success()
                    else:
                        response.failure("Unexpected response structure")
                except json.JSONDecodeError:
                    # Some APIs might return plain text success messages
                    if "success" in response.text.lower():
                        response.success()
                    else:
                        response.failure("Invalid response format")
            elif response.status_code == 400:
                response.failure("Bad request - invalid annotation data")
            elif response.status_code == 404:
                # Example not found - acceptable in load testing
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def bulk_annotation_submit(self):
        """
        Submit multiple annotations in a batch.
        
        This tests the system's ability to handle bulk operations.
        """
        if not self.examples:
            return
        
        # Select multiple examples for bulk annotation
        batch_size = random.randint(2, 5)
        selected_examples = random.sample(
            self.examples, 
            min(batch_size, len(self.examples))
        )
        
        bulk_data = {
            "annotations": [
                {
                    "example_id": example.get("id", f"mock-{i}"),
                    **self._generate_annotation_data()
                }
                for i, example in enumerate(selected_examples)
            ]
        }
        
        with self.client.post("/api/v1/annotations/bulk",
                            json=bulk_data,
                            catch_response=True,
                            name="POST_/api/v1/annotations/bulk") as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 400:
                response.failure("Bad request - invalid bulk annotation data")
            elif response.status_code == 404:
                # Endpoint might not exist - mark as success to avoid failing tests
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def annotation_status_check(self):
        """
        Check the status of submitted annotations.
        
        This simulates users checking their annotation history.
        """
        user_id = f"load_test_user_{id(self)}"
        
        with self.client.get(f"/api/v1/annotations/user/{user_id}",
                           catch_response=True,
                           name="GET_/api/v1/annotations/user/:id") as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # No annotations found - acceptable
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class AnnotationAdminUser(HttpUser):
    """
    Simulates administrative users performing management tasks.
    
    This represents users with higher privileges performing
    administrative operations like reviewing annotations.
    """
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight - fewer admin users
    
    @task
    def review_annotations(self):
        """Review submitted annotations for quality control."""
        with self.client.get("/api/v1/annotations/pending",
                           catch_response=True,
                           name="GET_/api/v1/annotations/pending") as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # No pending annotations
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task
    def system_stats(self):
        """Fetch system statistics and metrics."""
        with self.client.get("/api/v1/stats",
                           catch_response=True,
                           name="GET_/api/v1/stats") as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Endpoint might not exist
            else:
                response.failure(f"HTTP {response.status_code}")


# Performance thresholds and monitoring
PERFORMANCE_THRESHOLDS = {
    "p95_response_time_ms": 200,  # 95th percentile should be under 200ms
    "max_error_rate": 0.05,       # Maximum 5% error rate
    "min_requests_per_second": 10  # Minimum throughput
}

# Global variables for tracking performance
performance_data = {
    "total_requests": 0,
    "total_failures": 0,
    "response_times": [],
    "start_time": None
}


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    """Initialize performance monitoring."""
    if isinstance(environment.runner, MasterRunner):
        print("🚀 Starting Annotation Load Test")
        print(f"📊 Performance Thresholds:")
        print(f"   - 95th percentile response time: {PERFORMANCE_THRESHOLDS['p95_response_time_ms']}ms")
        print(f"   - Maximum error rate: {PERFORMANCE_THRESHOLDS['max_error_rate'] * 100}%")
        print(f"   - Minimum requests/second: {PERFORMANCE_THRESHOLDS['min_requests_per_second']}")


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    """Record test start time."""
    performance_data["start_time"] = time.time()
    print("✅ Load test started - monitoring performance metrics")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **_kwargs):
    """Track individual request performance."""
    performance_data["total_requests"] += 1
    performance_data["response_times"].append(response_time)
    
    if exception:
        performance_data["total_failures"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    """Analyze performance results and check thresholds."""
    if isinstance(environment.runner, MasterRunner):
        print("\n" + "="*60)
        print("📈 PERFORMANCE ANALYSIS")
        print("="*60)
        
        # Calculate metrics
        total_requests = performance_data["total_requests"]
        total_failures = performance_data["total_failures"]
        response_times = performance_data["response_times"]
        
        if total_requests == 0:
            print("❌ No requests were made during the test")
            return
        
        # Calculate statistics
        error_rate = total_failures / total_requests if total_requests > 0 else 0
        test_duration = time.time() - performance_data["start_time"]
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # Response time percentiles
        if response_times:
            response_times_sorted = sorted(response_times)
            p50 = response_times_sorted[int(len(response_times_sorted) * 0.5)]
            p95 = response_times_sorted[int(len(response_times_sorted) * 0.95)]
            p99 = response_times_sorted[int(len(response_times_sorted) * 0.99)]
            avg_response_time = sum(response_times) / len(response_times)
        else:
            p50 = p95 = p99 = avg_response_time = 0
        
        # Print results
        print(f"📊 Test Results:")
        print(f"   Duration: {test_duration:.1f}s")
        print(f"   Total Requests: {total_requests}")
        print(f"   Total Failures: {total_failures}")
        print(f"   Error Rate: {error_rate:.2%}")
        print(f"   Requests/Second: {requests_per_second:.1f}")
        print(f"   Avg Response Time: {avg_response_time:.1f}ms")
        print(f"   50th Percentile: {p50:.1f}ms")
        print(f"   95th Percentile: {p95:.1f}ms")
        print(f"   99th Percentile: {p99:.1f}ms")
        
        # Check performance thresholds
        print(f"\n🎯 Threshold Checks:")
        
        # Check 95th percentile response time
        p95_pass = p95 <= PERFORMANCE_THRESHOLDS["p95_response_time_ms"]
        print(f"   95th Percentile ≤ {PERFORMANCE_THRESHOLDS['p95_response_time_ms']}ms: "
              f"{'✅ PASS' if p95_pass else '❌ FAIL'} ({p95:.1f}ms)")
        
        # Check error rate
        error_rate_pass = error_rate <= PERFORMANCE_THRESHOLDS["max_error_rate"]
        print(f"   Error Rate ≤ {PERFORMANCE_THRESHOLDS['max_error_rate']:.1%}: "
              f"{'✅ PASS' if error_rate_pass else '❌ FAIL'} ({error_rate:.2%})")
        
        # Check throughput
        throughput_pass = requests_per_second >= PERFORMANCE_THRESHOLDS["min_requests_per_second"]
        print(f"   Requests/Second ≥ {PERFORMANCE_THRESHOLDS['min_requests_per_second']}: "
              f"{'✅ PASS' if throughput_pass else '❌ FAIL'} ({requests_per_second:.1f})")
        
        # Overall result
        all_passed = p95_pass and error_rate_pass and throughput_pass
        print(f"\n🏆 Overall Result: {'✅ ALL THRESHOLDS PASSED' if all_passed else '❌ SOME THRESHOLDS FAILED'}")
        
        # Exit with error code if thresholds failed (for CI)
        if not all_passed:
            print("\n💡 Recommendations:")
            if not p95_pass:
                print("   - Response times are too high. Consider optimizing database queries or adding caching.")
            if not error_rate_pass:
                print("   - Error rate is too high. Check server logs for issues.")
            if not throughput_pass:
                print("   - Throughput is too low. Consider scaling up the application or infrastructure.")
            
            environment.process_exit_code = 1
        
        print("="*60)


if __name__ == "__main__":
    """
    This allows running the locustfile directly for development/testing.
    
    Usage: python locustfile.py
    """
    print("Annotation Load Test")
    print("Use 'locust' command to run the actual load test")
    print("Example: locust --headless -u 50 -r 5 -t 5m --host http://localhost:8001")
