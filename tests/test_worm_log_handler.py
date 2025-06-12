"""
Pytest tests for WORM Log Handler with mocked S3 operations.

This test suite verifies:
1. JSON marshaling and S3 upload with correct key and Object Lock headers
2. Upload failure handling with retry logic and local error logging
"""
import json
import logging
import os
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from botocore.exceptions import ClientError

# Set up test environment
os.environ['AWS_S3_BUCKET'] = 'test-audit-logs-bucket'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_S3_PREFIX'] = 'test-audit-logs'

try:
    from shared.handlers.worm_log_handler import WORMLogHandler, WORMLogHandlerFactory
    from shared.logging_config import EnhancedJSONFormatter
    WORM_HANDLER_AVAILABLE = True
except ImportError as e:
    WORM_HANDLER_AVAILABLE = False

if not WORM_HANDLER_AVAILABLE:
    pytest.skip("WORM Handler not available", allow_module_level=True)


class TestWORMLogHandlerPytest:
    """Pytest test cases for WORM Log Handler with mocked S3."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Fixture providing a mocked S3 client."""
        with patch('boto3.client') as mock_boto_client:
            mock_s3_client = Mock()
            mock_boto_client.return_value = mock_s3_client
            mock_s3_client.head_bucket.return_value = True
            yield mock_s3_client
    
    @pytest.fixture
    def worm_handler(self, mock_s3_client):
        """Fixture providing a configured WORM handler."""
        handler = WORMLogHandler(
            s3_bucket='test-audit-logs-bucket',
            s3_region='us-east-1',
            s3_prefix='test-audit-logs',
            batch_size=1,  # Force immediate upload for testing
            upload_interval=1,  # Short interval for testing
            max_retries=1  # Reduced retries for faster testing
        )
        
        # Set up JSON formatter
        formatter = EnhancedJSONFormatter(
            reserved_attrs=[
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                'relativeCreated', 'thread', 'threadName', 'processName', 'process'
            ]
        )
        handler.setFormatter(formatter)
        
        yield handler
        
        # Cleanup
        handler.close()
    
    @pytest.fixture
    def test_log_record(self):
        """Fixture providing a test log record."""
        # Create test log record with audit context
        record = logging.LogRecord(
            name='test_service',
            level=logging.INFO,
            pathname='/app/test_service/main.py',
            lineno=123,
            msg='User login attempt successful',
            args=(),
            exc_info=None
        )
        
        # Add audit context fields
        record.service_name = 'test_service'
        record.request_id = 'req-12345-abcde'
        record.user_id = 'user123@example.com'
        record.action = 'user_login'
        record.created = datetime.now(timezone.utc).timestamp()
        
        return record
    
    def test_json_marshaling_and_s3_upload_with_object_lock(self, worm_handler, mock_s3_client, test_log_record):
        """
        Test 1: Mock S3 to verify that a sample LogRecord is marshaled to JSON 
        and uploaded with the right key and object lock headers.
        """
        # Arrange: Configure mock S3 client for successful upload
        mock_s3_client.put_object.return_value = {'ETag': '"mock-etag"'}
        
        # Act: Process the log record
        worm_handler.emit(test_log_record)
        
        # Give the handler a moment to process the upload
        time.sleep(0.1)
        worm_handler.flush()
        
        # Assert: Verify S3 put_object was called with correct parameters
        assert mock_s3_client.put_object.called, "S3 put_object should have been called"
        
        # Get the actual call arguments
        call_args, call_kwargs = mock_s3_client.put_object.call_args
        
        # Verify bucket and key format
        assert call_kwargs['Bucket'] == 'test-audit-logs-bucket'
        
        # Verify S3 key format: test-audit-logs/YYYY/MM/DD/req-12345-abcde-{uuid}.json
        s3_key = call_kwargs['Key']
        assert s3_key.startswith('test-audit-logs/')
        assert '/req-12345-abcde-' in s3_key
        assert s3_key.endswith('.json')
        
        # Verify key contains date structure (YYYY/MM/DD)
        key_parts = s3_key.split('/')
        assert len(key_parts) >= 4  # prefix/YYYY/MM/DD/filename.json
        assert len(key_parts[1]) == 4  # Year
        assert len(key_parts[2]) == 2  # Month
        assert len(key_parts[3]) == 2  # Day
        
        # Verify Object Lock headers
        assert call_kwargs['ObjectLockMode'] == 'GOVERNANCE'
        assert 'ObjectLockRetainUntilDate' in call_kwargs
        
        # Verify retention date is approximately 7 years in the future
        retain_until = call_kwargs['ObjectLockRetainUntilDate']
        expected_retain_until = datetime.now(timezone.utc) + timedelta(days=2557)
        time_diff = abs((retain_until - expected_retain_until).total_seconds())
        assert time_diff < 60, "Retention date should be approximately 7 years from now"
        
        # Verify content type and encoding
        assert call_kwargs['ContentType'] == 'application/json'
        
        # Verify metadata
        metadata = call_kwargs['Metadata']
        assert metadata['service_name'] == 'test_service'
        assert metadata['request_id'] == 'req-12345-abcde'
        assert metadata['log_level'] == 'INFO'
        assert 'timestamp' in metadata
        assert metadata['worm_handler_version'] == '1.0.0'
        
        # Verify JSON marshaling
        uploaded_json = call_kwargs['Body'].decode('utf-8')
        log_data = json.loads(uploaded_json)
        
        # Verify required fields in JSON
        assert log_data['service_name'] == 'test_service'
        assert log_data['request_id'] == 'req-12345-abcde'
        assert log_data['user_id'] == 'user123@example.com'
        assert log_data['action'] == 'user_login'
        assert log_data['level'] == 'INFO'
        assert log_data['message'] == 'User login attempt successful'
        assert 'timestamp' in log_data
        
        # Verify timestamp format (ISO 8601)
        timestamp = log_data['timestamp']
        assert timestamp.endswith('Z'), "Timestamp should be in UTC format"
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise exception
    
    def test_upload_failure_retry_and_local_error_logging(self, worm_handler, mock_s3_client, test_log_record, caplog):
        """
        Test 2: Simulate an upload failure (e.g. 5xx) and assert that the handler 
        retries once and then logs an ERROR locally without crashing the app.
        """
        # Arrange: Configure mock S3 client to fail with 5xx error
        error_response = {
            'Error': {
                'Code': 'InternalError',
                'Message': 'We encountered an internal error. Please try again.',
                'HTTPStatusCode': 500
            }
        }
        mock_s3_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Capture stderr output for handler error messages
        import io
        import sys
        captured_stderr = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured_stderr
        
        try:
            # Act: Process the log record (should trigger failure and retry)
            with caplog.at_level(logging.DEBUG):
                worm_handler.emit(test_log_record)
                
                # Give the handler time to process and retry
                time.sleep(0.2)
                worm_handler.flush()
                
                # Wait a bit more for background retry processing
                time.sleep(0.2)
            
            # Assert: Verify retry behavior
            # Should have called put_object multiple times (original + retries)
            assert mock_s3_client.put_object.call_count >= 2, f"Expected at least 2 calls (original + retry), got {mock_s3_client.put_object.call_count}"
            assert mock_s3_client.put_object.call_count <= 3, f"Expected at most 3 calls (original + 2 retries), got {mock_s3_client.put_object.call_count}"
            
            # Verify all calls had the same parameters (retry with same data)
            calls = mock_s3_client.put_object.call_args_list
            first_call_kwargs = calls[0][1]
            
            for call_args, call_kwargs in calls:
                assert call_kwargs['Bucket'] == first_call_kwargs['Bucket']
                assert call_kwargs['Key'] == first_call_kwargs['Key']
                assert call_kwargs['Body'] == first_call_kwargs['Body']
            
            # Assert: Verify local error logging
            stderr_output = captured_stderr.getvalue()
            
            # Should contain failure message after retries exhausted
            assert 'WORM Handler: Failed to upload log after' in stderr_output or \
                   'Failed to upload log' in stderr_output, \
                   f"Expected error message in stderr. Got: {stderr_output}"
            
            # Verify the error mentions retry count
            assert '1 retries' in stderr_output or 'retries' in stderr_output, \
                   f"Expected retry count in error message. Got: {stderr_output}"
            
            # Assert: Verify application doesn't crash
            # The handler should still be functional
            assert not worm_handler.shutdown_event.is_set(), "Handler should not be shut down"
            assert worm_handler.upload_thread.is_alive(), "Upload thread should still be alive"
            
            # Test that handler can still process new records (graceful degradation)
            test_record_2 = logging.LogRecord(
                name='test_service',
                level=logging.WARNING,
                pathname='/app/test.py',
                lineno=456,
                msg='Test message after failure',
                args=(),
                exc_info=None
            )
            test_record_2.service_name = 'test_service'
            test_record_2.request_id = 'req-67890-fghij'
            
            # This should not crash the application
            initial_call_count = mock_s3_client.put_object.call_count
            worm_handler.emit(test_record_2)
            time.sleep(0.1)
            
            # Verify handler attempted to process the new record
            assert mock_s3_client.put_object.call_count > initial_call_count, \
                   "Handler should attempt to process new records even after failures"
        
        finally:
            # Restore stderr
            sys.stderr = original_stderr
    
    def test_object_lock_fallback_behavior(self, worm_handler, mock_s3_client, test_log_record):
        """
        Test 3: Verify fallback behavior when Object Lock is not available.
        """
        # Arrange: Configure mock S3 client to reject Object Lock
        error_response = {
            'Error': {
                'Code': 'InvalidObjectState',
                'Message': 'Object Lock is not enabled for this bucket'
            }
        }
        
        # First call fails with Object Lock error, second succeeds without Object Lock
        mock_s3_client.put_object.side_effect = [
            ClientError(error_response, 'PutObject'),
            {'ETag': '"mock-etag"'}
        ]
        
        # Act: Process the log record
        worm_handler.emit(test_log_record)
        time.sleep(0.1)
        worm_handler.flush()
        
        # Assert: Verify two calls were made
        assert mock_s3_client.put_object.call_count == 2
        
        # Verify first call included Object Lock
        first_call = mock_s3_client.put_object.call_args_list[0][1]
        assert 'ObjectLockMode' in first_call
        assert 'ObjectLockRetainUntilDate' in first_call
        
        # Verify second call (fallback) did not include Object Lock
        second_call = mock_s3_client.put_object.call_args_list[1][1]
        assert 'ObjectLockMode' not in second_call
        assert 'ObjectLockRetainUntilDate' not in second_call
        
        # Verify fallback metadata includes object_lock status
        assert 'object_lock' in second_call['Metadata']
        assert second_call['Metadata']['object_lock'] == 'not_available'
    
    def test_json_formatter_integration(self, worm_handler, mock_s3_client):
        """
        Test 4: Verify integration with EnhancedJSONFormatter.
        """
        # Arrange: Create a log record with complex data
        record = logging.LogRecord(
            name='test_service',
            level=logging.ERROR,
            pathname='/app/auth.py',
            lineno=89,
            msg='Authentication failed for user %s',
            args=('malicious_user@evil.com',),
            exc_info=None
        )
        
        # Add complex audit context
        record.service_name = 'auth_service'
        record.request_id = 'req-auth-567'
        record.user_id = 'malicious_user@evil.com'
        record.action = 'failed_login'
        record.ip_address = '192.168.1.100'
        record.user_agent = 'Mozilla/5.0 (Malicious Browser)'
        record.failure_reason = 'invalid_password'
        record.attempt_count = 3
        
        mock_s3_client.put_object.return_value = {'ETag': '"mock-etag"'}
        
        # Act: Process the record
        worm_handler.emit(record)
        time.sleep(0.1)
        worm_handler.flush()        # Assert: Verify JSON structure
        call_kwargs = mock_s3_client.put_object.call_args[1]
        uploaded_json = call_kwargs['Body'].decode('utf-8')
        log_data = json.loads(uploaded_json)
        
        # Verify formatted message (with args interpolated)
        assert log_data['message'] == 'Authentication failed for user malicious_user@evil.com'
        
        # Verify all custom audit fields are preserved
        assert log_data['ip_address'] == '192.168.1.100'
        assert log_data['user_agent'] == 'Mozilla/5.0 (Malicious Browser)'
        assert log_data['failure_reason'] == 'invalid_password'
        assert log_data['attempt_count'] == 3
        
        # Verify essential logging fields that are included by the formatter
        assert log_data['level'] == 'ERROR'
        assert log_data['service_name'] == 'auth_service'
        assert log_data['request_id'] == 'req-auth-567'
        assert log_data['user_id'] == 'malicious_user@evil.com'
        assert log_data['action'] == 'failed_login'
        
        # Verify timestamp is present and properly formatted
        assert 'timestamp' in log_data
        timestamp = log_data['timestamp']
        assert timestamp.endswith('Z'), "Timestamp should be in UTC format"
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise exception
        
        # Verify the EnhancedJSONFormatter properly filters out reserved fields
        # These fields should NOT be present due to reserved_attrs configuration
        reserved_fields = ['name', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process']
        
        for field in reserved_fields:
            assert field not in log_data, f"Reserved field '{field}' should be filtered out by formatter"
        
        # Verify JSON structure includes expected fields
        expected_fields = {'message', 'level', 'timestamp', 'service_name', 'request_id', 
                          'user_id', 'action', 'ip_address', 'user_agent', 'failure_reason', 
                          'attempt_count'}
        actual_fields = set(log_data.keys())
        
        # All expected fields should be present
        missing_fields = expected_fields - actual_fields
        assert not missing_fields, f"Missing expected fields: {missing_fields}"
        
        # Verify audit fields
        assert log_data['service_name'] == 'auth_service'
        assert log_data['request_id'] == 'req-auth-567'
        assert log_data['user_id'] == 'malicious_user@evil.com'
        assert log_data['action'] == 'failed_login'
