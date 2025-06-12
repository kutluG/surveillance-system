"""
WORM (Write-Once-Read-Many) Log Handler for immutable audit log storage.

This handler uploads each log record to AWS S3 with Object Lock configuration,
ensuring tamper-proof audit trails for compliance requirements.
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import threading
from concurrent.futures import ThreadPoolExecutor
import queue

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class WORMLogHandler(logging.Handler):
    """
    Custom logging handler that uploads log records to S3 with WORM (Object Lock) configuration.
    
    Features:
    - Uploads each log record as a separate S3 object
    - Applies Object Lock with GOVERNANCE mode for compliance
    - Batches uploads for performance
    - Thread-safe with async upload queue
    - Graceful fallback if S3 is unavailable
    """
    
    def __init__(
        self,
        level: int = logging.INFO,
        s3_bucket: str = None,
        s3_region: str = None,
        s3_prefix: str = "audit-logs",
        retention_days: int = 2557,  # ~7 years for compliance
        batch_size: int = 10,
        upload_interval: int = 30,  # seconds
        max_retries: int = 3
    ):
        """
        Initialize WORM Log Handler.
        
        Args:
            level: Minimum logging level to handle
            s3_bucket: S3 bucket name (from AWS_S3_BUCKET env var)
            s3_region: AWS region (from AWS_REGION env var)
            s3_prefix: S3 key prefix (from AWS_S3_PREFIX env var)
            retention_days: Object Lock retention period in days
            batch_size: Number of logs to batch before uploading
            upload_interval: Maximum time to wait before uploading batch
            max_retries: Maximum retry attempts for failed uploads
        """
        super().__init__(level)
        
        # Configuration from environment variables
        self.s3_bucket = s3_bucket or os.getenv('AWS_S3_BUCKET')
        self.s3_region = s3_region or os.getenv('AWS_REGION', 'us-east-1')
        self.s3_prefix = s3_prefix or os.getenv('AWS_S3_PREFIX', 'audit-logs')
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.upload_interval = upload_interval
        self.max_retries = max_retries
        
        # Validation
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for WORMLogHandler. Install with: pip install boto3")
        
        if not self.s3_bucket:
            raise ValueError("S3 bucket must be specified via s3_bucket parameter or AWS_S3_BUCKET env var")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=self.s3_region)
            # Test connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Configure via AWS CLI or environment variables")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ValueError(f"S3 bucket '{self.s3_bucket}' not found")
            raise ValueError(f"Cannot access S3 bucket '{self.s3_bucket}': {e}")
        
        # Upload queue and thread management
        self.upload_queue = queue.Queue()
        self.batch_buffer = []
        self.last_upload_time = datetime.now()
        self.upload_lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Start background upload thread
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
        
        # Executor for async uploads
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="worm-upload")
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Process a log record and queue it for S3 upload.
        
        Args:
            record: The log record to process
        """
        try:
            # Format the record
            log_entry = self._format_record(record)
            
            # Add to upload queue
            self.upload_queue.put(log_entry, block=False)
            
        except Exception as e:
            # Avoid infinite recursion by not logging the error
            self.handleError(record)
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Format a log record for S3 storage.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log entry with metadata
        """
        # Get formatted message (applies any custom formatter)
        if self.formatter:
            message = self.formatter.format(record)
            # If formatter returns JSON, parse it
            try:
                log_data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, create structured format
                log_data = {
                    'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                    'level': record.levelname,
                    'service_name': getattr(record, 'service_name', 'unknown'),
                    'request_id': getattr(record, 'request_id', str(uuid.uuid4())),
                    'message': message,
                    'logger_name': record.name,
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
        else:
            # Create basic structured format
            log_data = {
                'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                'level': record.levelname,
                'service_name': getattr(record, 'service_name', 'unknown'),
                'request_id': getattr(record, 'request_id', str(uuid.uuid4())),
                'message': record.getMessage(),
                'logger_name': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'exc_info', 'exc_text', 'stack_info'):
                log_data[key] = value
        
        # Add metadata for S3 storage
        log_entry = {
            'log_data': log_data,
            'request_id': log_data.get('request_id', str(uuid.uuid4())),
            'timestamp': log_data['timestamp'],
            's3_key': self._generate_s3_key(log_data),
            'retry_count': 0
        }
        
        return log_entry
    
    def _generate_s3_key(self, log_data: Dict[str, Any]) -> str:
        """
        Generate S3 object key for log entry.
        
        Format: {AWS_S3_PREFIX}/YYYY/MM/DD/{request_id}-{uuid4}.json
        
        Args:
            log_data: Log data dictionary
            
        Returns:
            S3 object key
        """
        timestamp = datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00'))
        request_id = log_data.get('request_id', 'unknown')
        unique_id = str(uuid.uuid4())
        
        return f"{self.s3_prefix}/{timestamp.strftime('%Y/%m/%d')}/{request_id}-{unique_id}.json"
    
    def _upload_worker(self) -> None:
        """
        Background worker thread that uploads log batches to S3.
        """
        while not self.shutdown_event.is_set():
            try:
                # Wait for items in queue or timeout
                try:
                    log_entry = self.upload_queue.get(timeout=1.0)
                    self.batch_buffer.append(log_entry)
                except queue.Empty:
                    pass
                
                # Check if we should upload batch
                should_upload = (
                    len(self.batch_buffer) >= self.batch_size or
                    (self.batch_buffer and 
                     (datetime.now() - self.last_upload_time).seconds >= self.upload_interval)
                )
                
                if should_upload and self.batch_buffer:
                    with self.upload_lock:
                        batch_to_upload = self.batch_buffer.copy()
                        self.batch_buffer.clear()
                        self.last_upload_time = datetime.now()
                    
                    # Upload batch asynchronously
                    self.executor.submit(self._upload_batch, batch_to_upload)
                
            except Exception as e:
                # Log error to stderr to avoid infinite recursion
                print(f"WORM Handler upload worker error: {e}", file=sys.stderr)
    
    def _upload_batch(self, batch: list) -> None:
        """
        Upload a batch of log entries to S3.
        
        Args:
            batch: List of log entries to upload
        """
        for log_entry in batch:
            try:
                self._upload_single_log(log_entry)
            except Exception as e:
                # Retry logic
                if log_entry['retry_count'] < self.max_retries:
                    log_entry['retry_count'] += 1
                    self.upload_queue.put(log_entry, block=False)
                else:
                    # Log failure to stderr
                    print(f"WORM Handler: Failed to upload log after {self.max_retries} retries: {e}", 
                          file=sys.stderr)
    
    def _upload_single_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Upload a single log entry to S3 with Object Lock.
        
        Args:
            log_entry: Log entry to upload
        """
        # Prepare log data for upload
        log_json = json.dumps(log_entry['log_data'], ensure_ascii=False, indent=2)
        
        # Calculate retention until date
        retain_until = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
        
        # Upload to S3 with Object Lock
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=log_entry['s3_key'],
                Body=log_json.encode('utf-8'),
                ContentType='application/json',
                ObjectLockMode='GOVERNANCE',
                ObjectLockRetainUntilDate=retain_until,
                Metadata={
                    'service_name': log_entry['log_data'].get('service_name', 'unknown'),
                    'request_id': log_entry['request_id'],
                    'log_level': log_entry['log_data'].get('level', 'INFO'),
                    'timestamp': log_entry['timestamp'],
                    'worm_handler_version': '1.0.0'
                }
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidObjectState':
                # Object Lock not enabled on bucket
                # Upload without Object Lock as fallback
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=log_entry['s3_key'],
                    Body=log_json.encode('utf-8'),
                    ContentType='application/json',
                    Metadata={
                        'service_name': log_entry['log_data'].get('service_name', 'unknown'),
                        'request_id': log_entry['request_id'],
                        'log_level': log_entry['log_data'].get('level', 'INFO'),
                        'timestamp': log_entry['timestamp'],
                        'worm_handler_version': '1.0.0',
                        'object_lock': 'not_available'
                    }
                )
                print(f"WORM Handler: Object Lock not available, uploaded without lock: {log_entry['s3_key']}", 
                      file=sys.stderr)
            else:
                raise
    
    def flush(self) -> None:
        """
        Flush any pending log entries to S3.
        """
        # Upload any remaining items in buffer
        if self.batch_buffer:
            with self.upload_lock:
                batch_to_upload = self.batch_buffer.copy()
                self.batch_buffer.clear()
            
            self._upload_batch(batch_to_upload)
    
    def close(self) -> None:
        """
        Close the handler and cleanup resources.
        """
        # Signal shutdown
        self.shutdown_event.set()
        
        # Flush remaining logs
        self.flush()
        
        # Wait for upload thread to finish
        if self.upload_thread.is_alive():
            self.upload_thread.join(timeout=10)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        super().close()


class WORMLogHandlerFactory:
    """
    Factory class for creating WORM log handlers with different configurations.
    """
    
    @staticmethod
    def create_compliance_handler(
        service_name: str,
        s3_bucket: str = None,
        retention_years: int = 7
    ) -> WORMLogHandler:
        """
        Create a WORM handler configured for compliance requirements.
        
        Args:
            service_name: Name of the service
            s3_bucket: S3 bucket for audit logs
            retention_years: Retention period in years
            
        Returns:
            Configured WORM handler
        """
        from ..logging_config import EnhancedJSONFormatter
        
        handler = WORMLogHandler(
            level=logging.INFO,
            s3_bucket=s3_bucket,
            retention_days=retention_years * 365,
            batch_size=5,  # Smaller batches for compliance
            upload_interval=15  # Faster uploads for compliance
        )
        
        # Use enhanced JSON formatter
        formatter = EnhancedJSONFormatter(
            reserved_attrs=[
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                'relativeCreated', 'thread', 'threadName', 'processName', 'process'
            ]
        )
        handler.setFormatter(formatter)
        
        return handler
    
    @staticmethod
    def create_high_volume_handler(
        service_name: str,
        s3_bucket: str = None
    ) -> WORMLogHandler:
        """
        Create a WORM handler optimized for high-volume logging.
        
        Args:
            service_name: Name of the service
            s3_bucket: S3 bucket for audit logs
            
        Returns:
            Configured WORM handler optimized for high volume
        """
        from ..logging_config import EnhancedJSONFormatter
        
        handler = WORMLogHandler(
            level=logging.WARNING,  # Only warning and above for high volume
            s3_bucket=s3_bucket,
            batch_size=50,  # Larger batches
            upload_interval=60,  # Less frequent uploads
            max_retries=5
        )
        
        formatter = EnhancedJSONFormatter()
        handler.setFormatter(formatter)
        
        return handler


# Convenience function for easy integration
def add_worm_logging(
    logger: logging.Logger,
    service_name: str,
    s3_bucket: str = None,
    compliance_mode: bool = True
) -> WORMLogHandler:
    """
    Add WORM logging capability to an existing logger.
    
    Args:
        logger: Logger to add WORM handler to
        service_name: Name of the service
        s3_bucket: S3 bucket for audit logs
        compliance_mode: Whether to use compliance-optimized settings
        
    Returns:
        The created WORM handler
    """
    if compliance_mode:
        handler = WORMLogHandlerFactory.create_compliance_handler(service_name, s3_bucket)
    else:
        handler = WORMLogHandlerFactory.create_high_volume_handler(service_name, s3_bucket)
    
    logger.addHandler(handler)
    return handler
