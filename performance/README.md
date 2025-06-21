# Performance Testing with Locust

This directory contains load tests for the annotation backend using [Locust](https://locust.io/), a modern load testing framework written in Python. The tests simulate concurrent annotation submissions to benchmark performance and ensure the system can handle multiple users without degradation.

## 📁 Structure

```
performance/
├── locustfile.py                  # Main Locust test file with user behaviors
├── requirements-performance.txt   # Python dependencies for load testing
├── locust.conf                   # Locust configuration file
├── run-performance-tests.sh      # Linux/Mac test runner script
├── run-performance-tests.ps1     # Windows PowerShell test runner script
├── reports/                      # Generated test reports (created after tests)
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Python** (v3.8 or higher)
2. **Annotation backend** running on http://localhost:8001
3. **Required services** (PostgreSQL, Redis, Kafka)

### Install Dependencies

```bash
# Install performance testing dependencies
pip install -r requirements-performance.txt

# Or install Locust only
pip install locust
```

### Run Tests

#### Option 1: Using Scripts (Recommended)

**Linux/Mac:**
```bash
# Install dependencies
./run-performance-tests.sh install

# Check if backend is available
./run-performance-tests.sh check

# Run standard load test (50 users, 5m)
./run-performance-tests.sh standard

# Run custom test
./run-performance-tests.sh custom -u 100 -r 10 -t 10m

# Start web UI for interactive testing
./run-performance-tests.sh web
```

**Windows PowerShell:**
```powershell
# Install dependencies
.\run-performance-tests.ps1 -Command install

# Check backend availability
.\run-performance-tests.ps1 -Command check

# Run standard load test
.\run-performance-tests.ps1 -Command standard

# Run custom test
.\run-performance-tests.ps1 -Command custom -Users 100 -SpawnRate 10 -Duration 10m

# Start web UI
.\run-performance-tests.ps1 -Command web
```

#### Option 2: Direct Locust Commands

```bash
# Interactive web UI (recommended for development)
locust

# Headless test with specific parameters
locust --headless -u 50 -r 5 -t 5m --host http://localhost:8001

# CI mode with performance assertions
locust --headless -u 50 -r 5 -t 5m --host http://localhost:8001 --only-summary
```

## 🧪 Test Scenarios

### Predefined Test Scenarios

| Scenario | Users | Spawn Rate | Duration | Purpose |
|----------|-------|------------|----------|---------|
| **Light** | 10 | 2/s | 2m | Basic functionality check |
| **Standard** | 50 | 5/s | 5m | Normal load simulation |
| **Heavy** | 100 | 10/s | 10m | High load testing |
| **Stress** | 200 | 20/s | 15m | Stress testing |
| **CI** | 50 | 5/s | 5m | Automated CI/CD testing |

### User Behaviors

The load tests simulate two types of users:

#### 1. **AnnotationUser** (Primary Users)
- **Weight**: 9 (90% of users)
- **Tasks**:
  - `fetch_examples` (weight: 3) - Get available examples
  - `fetch_example_details` (weight: 2) - View specific example
  - `submit_annotation` (weight: 4) - Submit annotations
  - `bulk_annotation_submit` (weight: 1) - Batch operations
  - `annotation_status_check` (weight: 1) - Check status

#### 2. **AnnotationAdminUser** (Admin Users)
- **Weight**: 1 (10% of users)
- **Tasks**:
  - `review_annotations` - Quality control reviews
  - `system_stats` - System metrics access

### API Endpoints Tested

- `GET /health` - Health check
- `GET /api/v1/examples` - Fetch examples
- `GET /api/v1/examples/:id` - Get example details
- `POST /api/v1/examples/:id/label` - Submit annotation
- `POST /api/v1/annotations/bulk` - Bulk annotation submission
- `GET /api/v1/annotations/user/:id` - User annotation history
- `GET /api/v1/annotations/pending` - Pending reviews
- `GET /api/v1/stats` - System statistics

## 📊 Performance Thresholds

The tests enforce the following performance thresholds:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| **95th Percentile Response Time** | ≤ 200ms | 95% of requests complete within 200ms |
| **Error Rate** | ≤ 5% | Maximum 5% request failure rate |
| **Minimum Throughput** | ≥ 10 req/s | At least 10 requests per second |

### Automatic Threshold Checking

The Locust tests automatically:
1. ✅ Track response times and calculate percentiles
2. ✅ Monitor error rates
3. ✅ Calculate throughput metrics
4. ✅ Exit with error code if thresholds are exceeded
5. ✅ Generate detailed performance reports

## 🔧 Configuration

### Locust Configuration (`locust.conf`)

```ini
[locust]
locustfile = locustfile.py
host = http://localhost:8001
web-host = 0.0.0.0
web-port = 8089
loglevel = INFO
html = reports/load-test-report.html

[thresholds]
p95_response_time_ms = 200
max_error_rate = 0.05
min_requests_per_second = 10
```

### Environment Variables

```bash
# Target host
HOST=http://localhost:8001

# Logging level
LOCUST_LOGLEVEL=INFO

# Database connection (for backend)
DATABASE_URL=postgresql://user:pass@localhost:5432/events_db
REDIS_URL=redis://localhost:6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## 📈 Test Reports

Locust generates comprehensive reports:

### 1. **HTML Report**
- Interactive performance dashboard
- Request statistics and charts
- Response time distributions
- Failure analysis

### 2. **CSV Reports**
- `*_stats.csv` - Request statistics
- `*_failures.csv` - Failure details
- `*_exceptions.csv` - Exception details

### 3. **Console Output**
- Real-time performance metrics
- Threshold validation results
- Pass/fail determination

## 🚦 CI/CD Integration

### GitHub Actions Integration

The performance tests are integrated into the CI pipeline:

```yaml
performance-tests:
  runs-on: ubuntu-latest
  needs: python-lint-and-test
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  
  steps:
    - name: Run performance tests
      run: |
        locust --headless \
          --users 50 \
          --spawn-rate 5 \
          --run-time 5m \
          --host http://localhost:8001 \
          --only-summary \
          --stop-timeout 10
```

### Performance Monitoring

- ✅ **Automatic execution** on main branch pushes
- ✅ **Threshold validation** with automatic pass/fail
- ✅ **Performance reports** uploaded as artifacts
- ✅ **PR comments** with performance metrics
- ✅ **Historical tracking** via GitHub Actions

## 🛠️ Development and Debugging

### Running Individual Tests

```python
# Test specific user behavior
from locustfile import AnnotationUser
user = AnnotationUser()
user.submit_annotation()
```

### Custom Test Data

The tests automatically handle:
- **Mock data generation** when no real data exists
- **Realistic annotation payloads** with proper validation
- **Dynamic user identification** for tracking
- **Error handling** for missing endpoints

### Debugging Performance Issues

1. **Enable detailed logging**:
   ```bash
   locust --loglevel DEBUG
   ```

2. **Use web UI for real-time monitoring**:
   ```bash
   locust --web-host 0.0.0.0 --web-port 8089
   ```

3. **Analyze response time distributions**:
   - Check for outliers in the HTML report
   - Review CSV data for patterns
   - Monitor resource usage during tests

## 🔍 Troubleshooting

### Common Issues

**Tests failing with high response times:**
```bash
# Check backend logs for bottlenecks
# Monitor database connection pool
# Review Kafka consumer lag
# Check Redis memory usage
```

**Connection errors:**
```bash
# Verify backend is running
curl http://localhost:8001/health

# Check service dependencies
docker-compose ps
```

**Threshold failures in CI:**
```bash
# Review performance reports
# Check infrastructure scaling
# Analyze database query performance
```

### Performance Optimization Tips

1. **Database Optimization**:
   - Add indexes for frequently queried fields
   - Use connection pooling
   - Optimize query patterns

2. **Application Scaling**:
   - Increase worker processes
   - Use async/await patterns
   - Implement caching strategies

3. **Infrastructure**:
   - Scale horizontally with load balancers
   - Use Redis for caching
   - Optimize Kafka consumer configuration

## 📚 Advanced Usage

### Custom Load Shapes

Create custom load patterns:

```python
from locust import LoadTestShape

class CustomLoadShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()
        if run_time < 300:  # Ramp up for 5 minutes
            return (run_time // 10, 10)
        elif run_time < 600:  # Steady state
            return (50, 10)
        else:  # Ramp down
            return (max(0, 50 - (run_time - 600) // 10), 10)
```

### Distributed Testing

Run tests across multiple machines:

```bash
# Master node
locust --master --master-bind-host=* --master-bind-port=5557

# Worker nodes
locust --worker --master-host=<master-ip>
```

### Integration with Monitoring

Export metrics to external systems:

```python
from locust import events
import requests

@events.request_success.add_listener
def on_request_success(request_type, name, response_time, **kwargs):
    # Send metrics to monitoring system
    pass
```

## 🤝 Contributing

1. Follow existing test patterns
2. Add tests for new API endpoints
3. Update thresholds based on requirements
4. Document performance characteristics
5. Ensure tests pass in CI

## 📄 License

This performance testing suite is part of the surveillance system project and follows the same license terms.

---

**Performance Testing Checklist:**
- ✅ Backend health check passes
- ✅ All services (DB, Redis, Kafka) are running
- ✅ Test data is available or mocked
- ✅ Performance thresholds are met
- ✅ Reports are generated and reviewed
- ✅ Results are tracked over time
