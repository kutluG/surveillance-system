"""
S3 WORM Configuration Helper

This script helps set up an S3 bucket with Object Lock configuration
for immutable audit log storage.
"""
import boto3
import json
from typing import Optional
from botocore.exceptions import ClientError


class S3WORMSetup:
    """Helper class for configuring S3 buckets with WORM capabilities."""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize S3 WORM setup helper.
        
        Args:
            region: AWS region for the bucket
        """
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
    
    def create_worm_bucket(
        self,
        bucket_name: str,
        retention_days: int = 2557,  # 7 years
        enable_versioning: bool = True,
        enable_mfa_delete: bool = False
    ) -> bool:
        """
        Create an S3 bucket with Object Lock configuration for WORM storage.
        
        Args:
            bucket_name: Name of the S3 bucket to create
            retention_days: Number of days to retain objects
            enable_versioning: Whether to enable versioning (required for Object Lock)
            enable_mfa_delete: Whether to require MFA for delete operations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create bucket with Object Lock enabled
            if self.region == 'us-east-1':
                # us-east-1 doesn't require location constraint
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    ObjectLockEnabledForBucket=True
                )
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.region
                    },
                    ObjectLockEnabledForBucket=True
                )
            
            print(f"✓ Created bucket {bucket_name} with Object Lock enabled")
            
            # Configure versioning (required for Object Lock)
            if enable_versioning:
                mfa_delete = 'Enabled' if enable_mfa_delete else 'Disabled'
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={
                        'Status': 'Enabled',
                        'MfaDelete': mfa_delete
                    }
                )
                print(f"✓ Enabled versioning for {bucket_name}")
            
            # Configure default Object Lock retention
            self.s3_client.put_object_lock_configuration(
                Bucket=bucket_name,
                ObjectLockConfiguration={
                    'ObjectLockEnabled': 'Enabled',
                    'Rule': {
                        'DefaultRetention': {
                            'Mode': 'GOVERNANCE',
                            'Days': retention_days
                        }
                    }
                }
            )
            print(f"✓ Configured Object Lock with {retention_days} days retention")
            
            # Configure bucket policy for audit logging
            self._set_audit_bucket_policy(bucket_name)
            
            # Configure lifecycle policy
            self._set_lifecycle_policy(bucket_name, retention_days)
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyExists':
                print(f"⚠️  Bucket {bucket_name} already exists")
                return self._configure_existing_bucket(bucket_name, retention_days, enable_versioning)
            elif error_code == 'BucketAlreadyOwnedByYou':
                print(f"ℹ️  Bucket {bucket_name} already owned by you")
                return self._configure_existing_bucket(bucket_name, retention_days, enable_versioning)
            else:
                print(f"❌ Failed to create bucket {bucket_name}: {e}")
                return False
        except Exception as e:
            print(f"❌ Unexpected error creating bucket {bucket_name}: {e}")
            return False
    
    def _configure_existing_bucket(
        self,
        bucket_name: str,
        retention_days: int,
        enable_versioning: bool
    ) -> bool:
        """Configure an existing bucket for WORM storage."""
        try:
            # Check if Object Lock is already enabled
            try:
                self.s3_client.get_object_lock_configuration(Bucket=bucket_name)
                print(f"✓ Object Lock already enabled for {bucket_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ObjectLockConfigurationNotFoundError':
                    print(f"⚠️  Cannot enable Object Lock on existing bucket {bucket_name}")
                    print("   Object Lock must be enabled during bucket creation")
                    return False
                raise
            
            # Configure versioning if not already enabled
            if enable_versioning:
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={
                        'Status': 'Enabled'
                    }
                )
                print(f"✓ Ensured versioning is enabled for {bucket_name}")
            
            # Update Object Lock configuration
            self.s3_client.put_object_lock_configuration(
                Bucket=bucket_name,
                ObjectLockConfiguration={
                    'ObjectLockEnabled': 'Enabled',
                    'Rule': {
                        'DefaultRetention': {
                            'Mode': 'GOVERNANCE',
                            'Days': retention_days
                        }
                    }
                }
            )
            print(f"✓ Updated Object Lock retention to {retention_days} days")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure existing bucket {bucket_name}: {e}")
            return False
    
    def _set_audit_bucket_policy(self, bucket_name: str) -> None:
        """Set bucket policy for audit logging security."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyInsecureConnections",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ],
                    "Condition": {
                        "Bool": {
                            "aws:SecureTransport": "false"
                        }
                    }
                },
                {
                    "Sid": "DenyObjectDeletion",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": [
                        "s3:DeleteObject",
                        "s3:DeleteObjectVersion"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            print(f"✓ Applied security policy to {bucket_name}")
        except ClientError as e:
            print(f"⚠️  Could not apply bucket policy: {e}")
    
    def _set_lifecycle_policy(self, bucket_name: str, retention_days: int) -> None:
        """Set lifecycle policy for cost optimization."""
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'AuditLogTransition',
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        },
                        {
                            'Days': 365,
                            'StorageClass': 'DEEP_ARCHIVE'
                        }
                    ],
                    'Filter': {
                        'Prefix': 'audit-logs/'
                    }
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            print(f"✓ Applied lifecycle policy to {bucket_name}")
        except ClientError as e:
            print(f"⚠️  Could not apply lifecycle policy: {e}")
    
    def verify_worm_setup(self, bucket_name: str) -> bool:
        """
        Verify that the bucket is properly configured for WORM storage.
        
        Args:
            bucket_name: Name of the bucket to verify
            
        Returns:
            True if properly configured, False otherwise
        """
        try:
            print(f"🔍 Verifying WORM setup for {bucket_name}...")
            
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Bucket {bucket_name} exists and is accessible")
            
            # Check versioning
            versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            if versioning.get('Status') == 'Enabled':
                print("✓ Versioning is enabled")
            else:
                print("❌ Versioning is not enabled")
                return False
            
            # Check Object Lock configuration
            try:
                lock_config = self.s3_client.get_object_lock_configuration(Bucket=bucket_name)
                if lock_config['ObjectLockConfiguration']['ObjectLockEnabled'] == 'Enabled':
                    print("✓ Object Lock is enabled")
                    
                    rule = lock_config['ObjectLockConfiguration'].get('Rule', {})
                    default_retention = rule.get('DefaultRetention', {})
                    if default_retention:
                        mode = default_retention.get('Mode')
                        days = default_retention.get('Days', 0)
                        print(f"✓ Default retention: {mode} mode, {days} days")
                    else:
                        print("⚠️  No default retention configured")
                else:
                    print("❌ Object Lock is not enabled")
                    return False
            except ClientError as e:
                if e.response['Error']['Code'] == 'ObjectLockConfigurationNotFoundError':
                    print("❌ Object Lock is not configured")
                    return False
                raise
            
            print(f"✅ Bucket {bucket_name} is properly configured for WORM storage")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"❌ Bucket {bucket_name} not found")
            else:
                print(f"❌ Error verifying bucket {bucket_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error verifying bucket {bucket_name}: {e}")
            return False


def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup S3 bucket for WORM audit logging')
    parser.add_argument('bucket_name', help='Name of the S3 bucket')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--retention-days', type=int, default=2557, help='Retention period in days')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing bucket')
    
    args = parser.parse_args()
    
    setup = S3WORMSetup(region=args.region)
    
    if args.verify_only:
        success = setup.verify_worm_setup(args.bucket_name)
    else:
        success = setup.create_worm_bucket(
            bucket_name=args.bucket_name,
            retention_days=args.retention_days
        )
        if success:
            success = setup.verify_worm_setup(args.bucket_name)
    
    if success:
        print(f"\n🎉 S3 WORM setup successful for {args.bucket_name}")
        print("\nEnvironment variables to set:")
        print(f"export AWS_S3_BUCKET={args.bucket_name}")
        print(f"export AWS_REGION={args.region}")
        print("export AWS_S3_PREFIX=audit-logs")
        print("export ENABLE_WORM_LOGGING=true")
    else:
        print(f"\n❌ S3 WORM setup failed for {args.bucket_name}")
        exit(1)


if __name__ == '__main__':
    main()
