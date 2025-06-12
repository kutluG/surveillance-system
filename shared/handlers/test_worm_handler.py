"""
Test suite for WORM Log Handler and S3 integration.
"""
import json
import logging
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

# Set up test environment
os.environ['AWS_S3_BUCKET'] = 'test-audit-logs-bucket'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_S3_PREFIX'] = 'test-audit-logs'

try:
    from shared.handlers.worm_log_handler import WORMLogHandler, WORMLogHandlerFactory
    from shared.logging_config import configure_logging, configure_worm_logging
    WORM_HANDLER_AVAILABLE = True
except ImportError as e:
    WORM_HANDLER_AVAILABLE = False
    print(f"WORM Handler not available: {e}")


class TestWORMLogHandler(unittest.TestCase):
    """Test cases for WORM Log Handler."""
    
    def setUp(self):
        """Set up test environment."""
        if not WORM_HANDLER_AVAILABLE:
            self.skipTest("WORM Handler not available")
        
        self.test_bucket = 'test-audit-logs-bucket'
        self.test_region = 'us-east-1'
        self.test_prefix = 'test-audit-logs'
    
    @patch('boto3.client')
    def test_worm_handler_initialization(self, mock_boto_client):
        """Test WORM handler initialization."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create handler
        handler = WORMLogHandler(
            s3_bucket=self.test_bucket,
            s3_region=self.test_region,
            s3_prefix=self.test_prefix
        )
        
        # Verify initialization
        self.assertEqual(handler.s3_bucket, self.test_bucket)
        self.assertEqual(handler.s3_region, self.test_region)
        self.assertEqual(handler.s3_prefix, self.test_prefix)
        self.assertIsNotNone(handler.s3_client)
        
        # Cleanup
        handler.close()
    
    @patch('boto3.client')
    def test_log_record_formatting(self, mock_boto_client):
        """Test log record formatting for S3 upload."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create handler
        handler = WORMLogHandler(
            s3_bucket=self.test_bucket,
            s3_region=self.test_region,
            s3_prefix=self.test_prefix
        )
        
        # Create test log record
        logger = logging.getLogger('test_service')
        record = logging.LogRecord(
            name='test_service',
            level=logging.INFO,
            pathname='/test/path.py',
            lineno=123,
            msg='Test log message',
            args=(),
            exc_info=None
        )
        record.service_name = 'test_service'
        record.request_id = 'test-request-123'
        record.user_id = 'test-user'
        record.action = 'test_action'
        
        # Format record
        formatted = handler._format_record(record)
        
        # Verify format
        self.assertIn('log_data', formatted)
        self.assertIn('request_id', formatted)
        self.assertIn('timestamp', formatted)
        self.assertIn('s3_key', formatted)
        
        log_data = formatted['log_data']
        self.assertEqual(log_data['service_name'], 'test_service')
        self.assertEqual(log_data['request_id'], 'test-request-123')
        self.assertEqual(log_data['user_id'], 'test-user')
        self.assertEqual(log_data['action'], 'test_action')
        
        # Cleanup
        handler.close()
    
    @patch('boto3.client')
    def test_s3_key_generation(self, mock_boto_client):
        """Test S3 key generation format."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create handler
        handler = WORMLogHandler(
            s3_bucket=self.test_bucket,
            s3_region=self.test_region,
            s3_prefix=self.test_prefix
        )
        
        # Test key generation
        test_timestamp = datetime.now(timezone.utc).isoformat()
        log_data = {
            'timestamp': test_timestamp,
            'request_id': 'test-request-123'
        }
        
        s3_key = handler._generate_s3_key(log_data)
        
        # Verify key format: {prefix}/YYYY/MM/DD/{request_id}-{uuid}.json
        self.assertTrue(s3_key.startswith(self.test_prefix))
        self.assertTrue(s3_key.endswith('.json'))
        self.assertIn('test-request-123', s3_key)
        
        # Verify date format in path
        date_part = datetime.fromisoformat(test_timestamp.replace('Z', '+00:00'))
        expected_date_path = date_part.strftime('%Y/%m/%d')
        self.assertIn(expected_date_path, s3_key)
        
        # Cleanup
        handler.close()
    
    @patch('boto3.client')
    def test_s3_upload_with_object_lock(self, mock_boto_client):
        """Test S3 upload with Object Lock configuration."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        mock_s3_client.put_object.return_value = True
        
        # Create handler
        handler = WORMLogHandler(
            s3_bucket=self.test_bucket,
            s3_region=self.test_region,
            s3_prefix=self.test_prefix,
            retention_days=30
        )
        
        # Create test log entry
        log_entry = {
            'log_data': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': 'INFO',
                'service_name': 'test_service',
                'request_id': 'test-request-123',
                'message': 'Test log message'
            },
            'request_id': 'test-request-123',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            's3_key': 'test-audit-logs/2025/06/12/test-request-123-uuid.json',
            'retry_count': 0
        }
        
        # Upload log
        handler._upload_single_log(log_entry)
        
        # Verify S3 put_object was called with correct parameters
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        self.assertEqual(call_args[1]['Bucket'], self.test_bucket)
        self.assertEqual(call_args[1]['Key'], log_entry['s3_key'])
        self.assertEqual(call_args[1]['ContentType'], 'application/json')
        self.assertEqual(call_args[1]['ObjectLockMode'], 'GOVERNANCE')
        self.assertIn('ObjectLockRetainUntilDate', call_args[1])
        
        # Verify metadata
        metadata = call_args[1]['Metadata']
        self.assertEqual(metadata['service_name'], 'test_service')
        self.assertEqual(metadata['request_id'], 'test-request-123')
        self.assertEqual(metadata['log_level'], 'INFO')
        
        # Cleanup
        handler.close()
    
    @patch('boto3.client')
    def test_factory_compliance_handler(self, mock_boto_client):
        """Test factory method for compliance handler."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create compliance handler
        handler = WORMLogHandlerFactory.create_compliance_handler(
            service_name='test_service',
            s3_bucket=self.test_bucket,
            retention_years=7
        )
        
        # Verify configuration
        self.assertEqual(handler.s3_bucket, self.test_bucket)
        self.assertEqual(handler.retention_days, 7 * 365)
        self.assertEqual(handler.batch_size, 5)  # Smaller batches for compliance
        self.assertEqual(handler.upload_interval, 15)  # Faster uploads
        self.assertIsNotNone(handler.formatter)
        
        # Cleanup
        handler.close()
    
    @patch('boto3.client')
    def test_high_volume_handler(self, mock_boto_client):
        """Test factory method for high-volume handler."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create high-volume handler
        handler = WORMLogHandlerFactory.create_high_volume_handler(
            service_name='test_service',
            s3_bucket=self.test_bucket
        )
        
        # Verify configuration
        self.assertEqual(handler.s3_bucket, self.test_bucket)
        self.assertEqual(handler.level, logging.WARNING)  # Only warnings and above
        self.assertEqual(handler.batch_size, 50)  # Larger batches
        self.assertEqual(handler.upload_interval, 60)  # Less frequent uploads
        self.assertEqual(handler.max_retries, 5)
        
        # Cleanup
        handler.close()


class TestWORMIntegration(unittest.TestCase):
    """Integration tests for WORM logging with the main logging system."""
    
    def setUp(self):
        """Set up test environment."""
        if not WORM_HANDLER_AVAILABLE:
            self.skipTest("WORM Handler not available")
    
    @patch('boto3.client')
    def test_configure_logging_with_worm(self, mock_boto_client):
        """Test main logging configuration with WORM enabled."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Set environment variables
        os.environ['ENABLE_WORM_LOGGING'] = 'true'
        os.environ['AWS_S3_BUCKET'] = self.test_bucket = 'test-audit-logs-bucket'
        
        try:
            # Configure logging with WORM
            logger = configure_logging(
                service_name='test_service',
                log_level='INFO',
                enable_worm=True
            )
            
            # Verify logger was created
            self.assertIsNotNone(logger)
            self.assertEqual(logger.name, 'test_service')
            
            # Verify handlers were added
            root_logger = logging.getLogger()
            handler_types = [type(h).__name__ for h in root_logger.handlers]
            self.assertIn('StreamHandler', handler_types)  # Console handler
            self.assertIn('WORMLogHandler', handler_types)  # WORM handler
            
            # Test logging
            logger.info("Test message", extra={
                'action': 'test_logging',
                'user_id': 'test-user'
            })
            
        finally:
            # Cleanup environment
            os.environ.pop('ENABLE_WORM_LOGGING', None)
            # Close WORM handlers
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'close') and 'WORM' in type(handler).__name__:
                    handler.close()
    
    @patch('boto3.client')
    def test_add_worm_to_existing_logger(self, mock_boto_client):
        """Test adding WORM logging to existing logger."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = True
        
        # Create existing logger
        logger = configure_logging('test_service', 'INFO', enable_worm=False)
        
        # Add WORM logging
        worm_handler = configure_worm_logging(
            logger=logger,
            service_name='test_service',
            s3_bucket='test-audit-logs-bucket',
            compliance_mode=True
        )
        
        # Verify handler was added
        self.assertIsNotNone(worm_handler)
        self.assertIn(worm_handler, logger.handlers)
        
        # Test logging
        logger.warning("Test warning message", extra={
            'action': 'test_warning',
            'user_id': 'test-user'
        })
        
        # Cleanup
        worm_handler.close()


class TestMockS3Operations(unittest.TestCase):
    """Test S3 operations without actual AWS calls."""
    
    def test_s3_key_format_validation(self):
        """Test S3 key format meets requirements."""
        if not WORM_HANDLER_AVAILABLE:
            self.skipTest("WORM Handler not available")
        
        with patch('boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_boto.return_value = mock_s3_client
            mock_s3_client.head_bucket.return_value = True
            
            handler = WORMLogHandler(
                s3_bucket='test-bucket',
                s3_prefix='audit-logs'
            )
            
            # Test key generation with specific data
            log_data = {
                'timestamp': '2025-06-12T10:30:00Z',
                'request_id': 'req-12345-abcde'
            }
            
            s3_key = handler._generate_s3_key(log_data)
            
            # Verify format: {AWS_S3_PREFIX}/YYYY/MM/DD/<request_id>-<uuid4>.json
            expected_pattern = r'audit-logs/2025/06/12/req-12345-abcde-[a-f0-9-]{36}\.json'
            import re
            self.assertTrue(re.match(expected_pattern, s3_key))
            
            handler.close()


def run_worm_tests():
    """Run WORM logging tests."""
    print("🧪 Running WORM Log Handler Tests...")
    print("=" * 60)
    
    # Set up test environment
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestWORMLogHandler))
    suite.addTest(unittest.makeSuite(TestWORMIntegration))
    suite.addTest(unittest.makeSuite(TestMockS3Operations))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print results
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅' if success else '❌'} WORM Tests {'PASSED' if success else 'FAILED'}")
    
    return success


if __name__ == '__main__':
    run_worm_tests()
