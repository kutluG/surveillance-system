# 🔐 Encryption Deployment Guide

## Overview

This guide covers the deployment of encryption features for the surveillance system. All sensitive data (images, video files, annotations, labels) is encrypted at rest using AES-256-CBC encryption.

## 🚀 Quick Start

### 1. Generate Encryption Key

**⚠️ CRITICAL:** Generate a secure encryption key for production:

```bash
# Option 1: Use the provided script
python scripts/generate_encryption_key.py

# Option 2: Generate manually
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(32))"
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your generated encryption key
nano .env
```

Set the `ENCRYPTION_KEY` to your generated value:
```bash
ENCRYPTION_KEY=your_64_character_hex_key_here
```

### 3. Deploy Services

```bash
# Start all services with encryption enabled
docker-compose up -d
```

## 🔧 Configuration Details

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENCRYPTION_KEY` | 32-byte hex key for AES-256-CBC | `a1b2c3d4...` (64 chars) |

### Encrypted Components

1. **VMS Service Storage**
   - All video files encrypted before storage (S3/local disk)
   - Automatic encryption/decryption in storage layer

2. **Database Fields**
   - Annotation labels encrypted using SQLAlchemy TypeDecorator
   - Bounding box coordinates encrypted
   - Frame metadata encrypted

3. **Mobile App**
   - Client-side AES-256-CBC encryption for offline cache
   - Device-unique key derivation with PBKDF2

## 🔒 Security Best Practices

### Key Management

1. **Generate Unique Keys per Environment**
   ```bash
   # Development
   python -c "import secrets; print('DEV_ENCRYPTION_KEY=' + secrets.token_hex(32))"
   
   # Production
   python -c "import secrets; print('PROD_ENCRYPTION_KEY=' + secrets.token_hex(32))"
   ```

2. **Secure Key Storage**
   - Use environment variables (never hardcode)
   - Consider using secret management systems (AWS Secrets Manager, HashiCorp Vault)
   - Keep backups of production keys in secure, separate location

3. **Key Rotation**
   - Plan for periodic key rotation
   - Test key rotation procedures in staging environment
   - Maintain access to old keys for data recovery

### Deployment Security

1. **Environment Files**
   ```bash
   # Set proper permissions
   chmod 600 .env
   
   # Ensure .env is in .gitignore
   echo ".env" >> .gitignore
   ```

2. **Container Security**
   ```bash
   # Use secrets in production instead of environment files
   docker secret create encryption_key /path/to/key/file
   ```

## 🧪 Testing Encryption

### Pre-Deployment Tests

1. **Crypto Tests**
   ```bash
   # Run encryption unit tests
   python -m pytest tests/test_crypto.py -v
   
   # Run integration tests
   python -m pytest tests/test_integration_encryption.py -v
   ```

2. **Storage Tests**
   ```bash
   # Test encrypted storage
   python -m pytest vms_service/tests/test_encrypted_storage.py -v
   ```

3. **End-to-End Tests**
   ```bash
   # Test full encryption pipeline
   python -m pytest tests/test_e2e_encryption.py -v
   ```

### Post-Deployment Validation

1. **Verify Encryption is Active**
   ```bash
   # Run the encryption verification script
   python scripts/verify_encryption.py
   
   # Check storage files are encrypted (if any exist)
   cd data/clips
   file *.mp4  # Should show encrypted/binary data
   
   # Check database encryption
   docker-compose exec postgres psql -U user -d events_db -c "SELECT * FROM annotations LIMIT 1;"
   # Labels should appear as encrypted strings
   ```

2. **Test Data Recovery**
   ```bash
   # Test decryption works
   curl -X GET "http://localhost:8008/clips/test_video.mp4"
   # Should return decrypted video
   ```

## 🚨 Troubleshooting

### Common Issues

1. **Missing Encryption Key**
   ```
   EncryptionError: ENCRYPTION_KEY not configured
   ```
   **Solution:** Set the `ENCRYPTION_KEY` environment variable

2. **Invalid Key Length**
   ```
   EncryptionError: Key must be exactly 32 bytes (64 hex characters)
   ```
   **Solution:** Generate a proper 64-character hex key

3. **Key Mismatch on Decryption**
   ```
   EncryptionError: Decryption failed - invalid key or corrupted data
   ```
   **Solution:** Ensure the same key is used for encryption and decryption

### Recovery Procedures

1. **Lost Encryption Key**
   - If production key is lost, encrypted data cannot be recovered
   - Restore from backup with known key
   - This is why key backup is critical

2. **Corrupted Encrypted Data**
   - Check file integrity
   - Restore from backup
   - Investigate storage system issues

## 📊 Monitoring

### Metrics to Monitor

1. **Encryption Performance**
   - Encryption/decryption latency
   - Storage throughput
   - CPU usage during crypto operations

2. **Error Rates**
   - Failed encryption operations
   - Decryption failures
   - Key-related errors

### Alerting

Set up alerts for:
- Encryption service failures
- High crypto operation latency
- Unusually high decryption failure rates

## 🔄 Migration Guide

### From Unencrypted to Encrypted

1. **Backup All Data**
   ```bash
   # Backup database
   docker-compose exec postgres pg_dump -U user events_db > backup.sql
   
   # Backup video files
   tar -czf video_backup.tar.gz data/clips/
   ```

2. **Encrypt Existing Data**
   ```bash
   # Run migration script (to be created if needed)
   python scripts/migrate_to_encryption.py
   ```

3. **Verify Migration**
   ```bash
   # Test encrypted data access
   python scripts/verify_encryption_migration.py
   ```

## 📋 Production Deployment Checklist

- [ ] Generated secure encryption key
- [ ] Configured `.env` with encryption key
- [ ] Set proper file permissions (600) on `.env`
- [ ] Verified encryption key is 64 hex characters
- [ ] Backed up encryption key securely
- [ ] Ran pre-deployment tests
- [ ] Updated all service configurations
- [ ] Tested data storage and retrieval
- [ ] Configured monitoring and alerting
- [ ] Documented key management procedures
- [ ] Trained team on encryption procedures

## 🆘 Support

If you encounter issues with encryption deployment:

1. Check the logs: `docker-compose logs vms_service`
2. Verify environment configuration: `python -c "from shared.config import settings; print(settings.encryption_key[:8] + '...')"` 
3. Run diagnostic tests: `python -m pytest tests/test_crypto.py::test_environment_integration -v`
4. Check the troubleshooting section above

---

**⚠️ Security Reminder:** The encryption key is the master key for all your data. Treat it with the highest security standards - never commit to version control, always use secure backup methods, and restrict access to authorized personnel only.
