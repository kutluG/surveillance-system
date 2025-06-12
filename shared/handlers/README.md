# WORM Audit Log Storage Implementation

## Overview

This implementation provides immutable WORM (Write-Once-Read-Many) audit log storage for the surveillance system, ensuring all structured JSON audit logs are written to an append-only, tamper-proof store in AWS S3 with Object Lock configuration.

## Features

- **Immutable Storage**: Uses AWS S3 Object Lock with GOVERNANCE mode for tamper-proof audit trails
- **Structured JSON**: All logs are formatted as structured JSON with consistent schemas
- **High Performance**: Batched uploads with configurable batch sizes and intervals
- **Thread-Safe**: Concurrent logging with background upload workers
- **Retry Logic**: Automatic retry on failures with exponential backoff
- **Compliance Ready**: 7-year default retention period for regulatory compliance
- **Cost Optimized**: Automatic lifecycle transitions to reduce storage costs

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│  WORM Handler    │───▶│   S3 Bucket     │
│   Logging       │    │  (Batching &     │    │  (Object Lock   │
│                 │    │   Upload Queue)  │    │   Enabled)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Background      │
                       │  Upload Worker   │
                       │  Thread          │
                       └──────────────────┘
```

## Components

### 1. WORMLogHandler

Main logging handler that:
- Accepts log records from the Python logging system
- Formats records as structured JSON
- Queues records for batch upload
- Manages background upload workers
- Handles retry logic and error recovery

### 2. S3WORMSetup

Configuration utility that:
- Creates S3 buckets with Object Lock enabled
- Configures retention policies
- Sets up security policies
- Applies lifecycle rules for cost optimization

### 3. Integration with Existing Logging

Seamlessly integrates with the existing logging infrastructure:
- Works alongside console logging
- Uses the same JSON formatters and filters
- Maintains request correlation IDs
- Preserves all audit context

## Configuration

### Environment Variables

```bash
# Required
AWS_S3_BUCKET=your-audit-logs-bucket
AWS_REGION=us-east-1

# Optional
AWS_S3_PREFIX=audit-logs              # S3 key prefix
ENABLE_WORM_LOGGING=true             # Enable WORM logging
LOG_LEVEL=INFO                       # Logging level

# AWS Credentials (via standard AWS methods)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### S3 Bucket Setup

1. **Create bucket with Object Lock**:
   ```bash
   python shared/handlers/s3_worm_setup.py your-audit-logs-bucket --region us-east-1
   ```

2. **Verify configuration**:
   ```bash
   python shared/handlers/s3_worm_setup.py your-audit-logs-bucket --verify-only
   ```

## Usage Examples

### 1. Enable WORM Logging in Service

```python
from shared.logging_config import configure_logging

# Automatic WORM enabling via environment variable
os.environ['ENABLE_WORM_LOGGING'] = 'true'
logger = configure_logging('my_service')

# Manual WORM configuration
logger = configure_logging('my_service', enable_worm=True)
```

### 2. Add WORM to Existing Logger

```python
from shared.logging_config import configure_worm_logging

# Add WORM capability to existing logger
worm_handler = configure_worm_logging(
    logger=existing_logger,
    service_name='my_service',
    s3_bucket='my-audit-logs-bucket',
    compliance_mode=True
)
```

### 3. Factory Methods

```python
from shared.handlers.worm_log_handler import WORMLogHandlerFactory

# Compliance-optimized handler (7-year retention, frequent uploads)
compliance_handler = WORMLogHandlerFactory.create_compliance_handler(
    service_name='my_service',
    s3_bucket='audit-logs-bucket',
    retention_years=7
)

# High-volume optimized handler (warnings only, larger batches)
volume_handler = WORMLogHandlerFactory.create_high_volume_handler(
    service_name='my_service',
    s3_bucket='audit-logs-bucket'
)
```

## S3 Object Structure

### Object Key Format
```
{AWS_S3_PREFIX}/YYYY/MM/DD/{request_id}-{uuid4}.json
```

Example:
```
audit-logs/2025/06/12/req-12345-abcde-550e8400-e29b-41d4-a716-446655440000.json
```

### Object Content
```json
{
  "timestamp": "2025-06-12T10:30:00.123Z",
  "level": "INFO",
  "service_name": "camera_service",
  "request_id": "req-12345-abcde",
  "user_id": "user123",
  "camera_id": "cam001",
  "action": "motion_detected",
  "message": "Motion detected in camera cam001",
  "logger_name": "camera_service",
  "module": "motion_detector",
  "function": "process_frame",
  "line": 245,
  "confidence": 0.92,
  "detection_count": 3
}
```

### Object Metadata
```
service_name: camera_service
request_id: req-12345-abcde
log_level: INFO
timestamp: 2025-06-12T10:30:00.123Z
worm_handler_version: 1.0.0
```

## Object Lock Configuration

- **Mode**: GOVERNANCE (allows bypass with special permissions)
- **Retention**: 2557 days (7 years) by default
- **Legal Hold**: Not used (can be added per object if needed)

## Security Features

### Bucket Policy
- **Deny insecure connections**: Requires HTTPS/TLS
- **Deny object deletion**: Prevents accidental or malicious deletion
- **Restrict access**: Only authorized services can write

### Object Lock Benefits
- **Immutability**: Objects cannot be modified or deleted during retention period
- **Compliance**: Meets regulatory requirements for audit log retention
- **Tamper-proof**: Cryptographic integrity verification

## Cost Optimization

### Lifecycle Policy
- **Day 1-30**: Standard storage
- **Day 31-90**: Standard-IA (Infrequent Access)
- **Day 91-365**: Glacier storage
- **Day 366+**: Deep Archive storage

### Estimated Costs (us-east-1)
- Standard (30 days): ~$0.023/GB/month
- Standard-IA (60 days): ~$0.0125/GB/month  
- Glacier (275 days): ~$0.004/GB/month
- Deep Archive (remaining): ~$0.00099/GB/month

## Performance Characteristics

### Batching Configuration
- **Compliance Mode**: 5 logs per batch, 15-second intervals
- **High-Volume Mode**: 50 logs per batch, 60-second intervals
- **Custom**: Configurable batch size and intervals

### Threading
- **Background Workers**: 1 upload worker thread per handler
- **Thread Pool**: 2 concurrent upload threads for S3 operations
- **Queue Management**: Thread-safe queue with configurable capacity

### Retry Logic
- **Max Retries**: 3 by default (configurable)
- **Exponential Backoff**: Built into boto3 client
- **Error Handling**: Graceful degradation without blocking application

## Monitoring and Troubleshooting

### Success Indicators
```bash
# Check if WORM logging is enabled
grep "WORM audit logging enabled" application.log

# Verify S3 uploads
aws s3 ls s3://your-audit-logs-bucket/audit-logs/ --recursive
```

### Error Scenarios

1. **S3 Bucket Not Found**
   ```
   Error: Cannot access S3 bucket 'bucket-name': The specified bucket does not exist
   ```
   Solution: Create bucket or verify name/permissions

2. **Object Lock Not Enabled**
   ```
   Warning: Object Lock not available, uploaded without lock
   ```
   Solution: Enable Object Lock during bucket creation

3. **AWS Credentials Missing**
   ```
   Error: AWS credentials not found
   ```
   Solution: Configure AWS credentials via CLI, environment, or IAM roles

### Debug Logging
Enable debug logging to troubleshoot:
```python
import logging
logging.getLogger('shared.handlers.worm_log_handler').setLevel(logging.DEBUG)
```

## Testing

### Unit Tests
```bash
cd shared/handlers
python test_worm_handler.py
```

### Integration Test
```bash
# Test with mock S3
python -c "
from shared.handlers.test_worm_handler import run_worm_tests
run_worm_tests()
"
```

### Manual Test
```python
from shared.logging_config import configure_logging
import os

os.environ['AWS_S3_BUCKET'] = 'your-test-bucket'
os.environ['ENABLE_WORM_LOGGING'] = 'true'

logger = configure_logging('test_service')
logger.info('Test audit log', extra={
    'action': 'manual_test',
    'user_id': 'test_user'
})
```

## Migration Guide

### From Existing Logging

1. **Install dependencies**:
   ```bash
   pip install boto3 python-json-logger
   ```

2. **Set environment variables**:
   ```bash
   export AWS_S3_BUCKET=your-audit-logs-bucket
   export ENABLE_WORM_LOGGING=true
   ```

3. **Update service initialization**:
   ```python
   # Before
   logger = configure_logging('my_service')
   
   # After (no change needed if using environment variables)
   logger = configure_logging('my_service')
   ```

### Gradual Rollout

1. **Phase 1**: Deploy with WORM disabled, verify normal operation
2. **Phase 2**: Enable WORM for non-critical services
3. **Phase 3**: Enable WORM for all services
4. **Phase 4**: Remove console logging if desired (compliance environments)

## Compliance Considerations

### Regulatory Requirements
- **SOX**: 7-year retention period supported
- **HIPAA**: Immutable audit trails with access controls
- **PCI DSS**: Tamper-proof log storage with integrity verification
- **GDPR**: Right to erasure supported via special procedures

### Audit Trail Features
- **Chronological ordering**: Timestamp-based organization
- **Non-repudiation**: Cryptographic integrity via S3
- **User attribution**: User ID tracking in all log entries
- **Action tracking**: Detailed action logging with context

## Troubleshooting Common Issues

### 1. Slow Upload Performance
- Increase batch size: `batch_size=50`
- Increase upload interval: `upload_interval=60`
- Use high-volume handler factory

### 2. High S3 Costs
- Verify lifecycle policy is applied
- Monitor storage class transitions
- Consider reducing retention period if compliant

### 3. Missing Log Entries
- Check application shutdown procedures
- Ensure `handler.flush()` and `handler.close()` are called
- Verify retry logic isn't exhausted

### 4. Object Lock Errors
- Verify bucket was created with Object Lock enabled
- Check IAM permissions for Object Lock operations
- Ensure retention date is in the future

## Future Enhancements

### Planned Features
- **Log encryption**: Client-side encryption before upload
- **Log signing**: Digital signatures for non-repudiation
- **Multi-region replication**: Cross-region backup for DR
- **Real-time monitoring**: CloudWatch integration for alerts
- **Log analytics**: Integration with AWS CloudTrail Insights

### Extension Points
- **Custom formatters**: Pluggable log formatting
- **Multiple backends**: Support for other cloud providers
- **Compression**: Gzip compression for large logs
- **Deduplication**: Hash-based deduplication for repeated logs

## Support and Maintenance

For issues, questions, or contributions:
1. Check existing documentation and troubleshooting guides
2. Run test suite to verify installation
3. Enable debug logging for detailed diagnostics
4. Create issue with logs and configuration details
