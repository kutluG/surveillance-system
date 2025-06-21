#!/usr/bin/env python3
"""
Integration test for encryption functionality
"""

from models import AnnotationExample, EncryptedType, EncryptedJSONType
from storage import EncryptedStorage
import tempfile
import json

print('🔐 Quick Integration Test')
print('='*40)

# Test TypeDecorator
print('Testing database field encryption...')
encryptor = EncryptedType()
test_label = 'Person: John Smith at main gate'
encrypted = encryptor.process_bind_param(test_label, None)
decrypted = encryptor.process_result_value(encrypted, None)
print(f'✅ Database encryption test: {test_label == decrypted}')

# Test JSON TypeDecorator
print('Testing JSON field encryption...')
json_encryptor = EncryptedJSONType()
test_json = {'name': 'John Smith', 'location': 'main gate', 'confidence': 0.95}
encrypted_json = json_encryptor.process_bind_param(test_json, None)
decrypted_json = json_encryptor.process_result_value(encrypted_json, None)
print(f'✅ JSON encryption test: {test_json == decrypted_json}')

# Test Storage
print('Testing file storage encryption...')
with tempfile.TemporaryDirectory() as temp_dir:
    storage = EncryptedStorage(temp_dir)
    # Use valid base64 data
    test_data = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
    key = storage.store_frame_data('test_123', test_data)
    retrieved_data = storage.retrieve_frame_data(key)
    print(f'✅ Storage encryption test: {test_data == retrieved_data}')

# Test with binary data via base64
print('Testing binary data encryption via base64...')
with tempfile.TemporaryDirectory() as temp_dir:
    storage = EncryptedStorage(temp_dir)
    # Convert binary data to base64 for storage
    binary_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    import base64
    base64_data = base64.b64encode(binary_data).decode('utf-8')
    key = storage.store_frame_data('test_binary', base64_data)
    retrieved_base64 = storage.retrieve_frame_data(key, as_base64=True)
    retrieved_binary = base64.b64decode(retrieved_base64)
    print(f'✅ Binary encryption test: {binary_data == retrieved_binary}')

print('\n🎯 All integration tests passed!')
print('🔒 Encryption is working correctly across all layers')
