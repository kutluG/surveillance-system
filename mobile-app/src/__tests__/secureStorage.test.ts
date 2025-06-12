import secureStorage from '../utils/secureStorage';

// Mock the native modules
jest.mock('react-native-encrypted-storage', () => ({
  setItem: jest.fn(),
  getItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  getAllKeys: jest.fn(),
}));

jest.mock('react-native-aes-crypto', () => ({
  AES: {
    encrypt: jest.fn(),
    decrypt: jest.fn(),
  },
  PBKDF2: jest.fn(),
  sha256: jest.fn(),
}));

jest.mock('react-native-device-info', () => ({
  getUniqueId: jest.fn(() => Promise.resolve('mock-device-id')),
}));

jest.mock('react-native-keychain', () => ({
  setInternetCredentials: jest.fn(),
  getInternetCredentials: jest.fn(),
  resetInternetCredentials: jest.fn(),
  ACCESS_CONTROL: {
    BIOMETRY_CURRENT_SET: 'BiometryCurrentSet',
  },
  ACCESSIBLE: {
    WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WhenUnlockedThisDeviceOnly',
  },
}));

describe('SecureStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize successfully', async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      PBKDF2.mockResolvedValue('mock-encryption-key');
      Keychain.getInternetCredentials.mockResolvedValue(false);
      Keychain.setInternetCredentials.mockResolvedValue(true);

      await expect(secureStorage.initialize()).resolves.not.toThrow();
    });    it('should handle initialization failure gracefully', async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      // Make sure key doesn't exist to trigger generation
      Keychain.getInternetCredentials.mockResolvedValue(false);
      PBKDF2.mockRejectedValue(new Error('Key generation failed'));

      await expect(secureStorage.initialize()).rejects.toThrow();
    });
  });

  describe('Data Storage and Retrieval', () => {
    beforeEach(async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      PBKDF2.mockResolvedValue('mock-encryption-key');
      Keychain.getInternetCredentials.mockResolvedValue(false);
      Keychain.setInternetCredentials.mockResolvedValue(true);
      
      await secureStorage.initialize();
    });

    it('should store and retrieve data securely', async () => {      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      const testData = { token: 'test-auth-token', userId: '12345' };
      const testKey = 'auth_token';
      const encryptedData = 'encrypted-test-data';
      
      AES.encrypt.mockResolvedValue(encryptedData);
      AES.decrypt.mockResolvedValue(JSON.stringify(testData));
      EncryptedStorage.setItem.mockResolvedValue();
      EncryptedStorage.getItem.mockResolvedValue(JSON.stringify({
        iv: 'test-iv',
        data: encryptedData,
        timestamp: Date.now()
      }));

      // Store data
      await secureStorage.setItem(testKey, JSON.stringify(testData));
      expect(AES.encrypt).toHaveBeenCalled();
      
      // Should store data as JSON with metadata
      const setItemCall = EncryptedStorage.setItem.mock.calls[0];
      expect(setItemCall[0]).toBe(testKey);
      const storedData = JSON.parse(setItemCall[1]);
      expect(storedData).toHaveProperty('iv');
      expect(storedData).toHaveProperty('data');
      expect(storedData).toHaveProperty('timestamp');
      expect(storedData.data).toBe(encryptedData);

      // Retrieve data
      const retrievedData = await secureStorage.getItem(testKey);
      expect(EncryptedStorage.getItem).toHaveBeenCalledWith(testKey);
      expect(AES.decrypt).toHaveBeenCalled();
      expect(retrievedData).toBe(JSON.stringify(testData));
    });

    it('should return null for non-existent keys', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      EncryptedStorage.getItem.mockResolvedValue(null);

      const result = await secureStorage.getItem('non-existent-key');
      expect(result).toBeNull();
    });

    it('should handle decryption failure gracefully', async () => {
      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      const encryptedData = 'corrupted-encrypted-data';
      
      EncryptedStorage.getItem.mockResolvedValue(encryptedData);
      AES.decrypt.mockRejectedValue(new Error('Decryption failed'));
      EncryptedStorage.removeItem.mockResolvedValue();

      const result = await secureStorage.getItem('corrupted-key');
      
      // Should clean up corrupted data and return null
      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith('corrupted-key');
      expect(result).toBeNull();
    });

    it('should remove items successfully', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      EncryptedStorage.removeItem.mockResolvedValue();

      await secureStorage.removeItem('test-key');
      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith('test-key');
    });

    it('should clear all data', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      EncryptedStorage.clear.mockResolvedValue();

      await secureStorage.clear();
      expect(EncryptedStorage.clear).toHaveBeenCalled();
    });

    it('should get all keys', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      const mockKeys = ['auth_token', 'user_data', 'settings'];
      
      EncryptedStorage.getAllKeys.mockResolvedValue(mockKeys);

      const keys = await secureStorage.getAllKeys();
      expect(EncryptedStorage.getAllKeys).toHaveBeenCalled();
      expect(keys).toEqual(mockKeys);
    });
  });

  describe('Error Handling', () => {
    beforeEach(async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      PBKDF2.mockResolvedValue('mock-encryption-key');
      Keychain.getInternetCredentials.mockResolvedValue(false);
      Keychain.setInternetCredentials.mockResolvedValue(true);
      
      await secureStorage.initialize();
    });

    it('should handle storage errors gracefully', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      EncryptedStorage.setItem.mockRejectedValue(new Error('Storage full'));

      await expect(secureStorage.setItem('test', 'data')).rejects.toThrow();
    });

    it('should handle retrieval errors gracefully', async () => {
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      EncryptedStorage.getItem.mockRejectedValue(new Error('Read error'));

      const result = await secureStorage.getItem('test-key');
      expect(result).toBeNull();
    });
  });

  describe('Encryption Key Management', () => {
    it('should use existing key when available', async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      const existingKey = 'existing-encryption-key';
      Keychain.getInternetCredentials.mockResolvedValue({
        password: existingKey,
      });

      await secureStorage.initialize();
      
      // Should not generate new key
      expect(PBKDF2).not.toHaveBeenCalled();
    });    it('should generate new key when none exists', async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const Keychain = require('react-native-keychain');
      
      // Clear all previous calls
      jest.clearAllMocks();
      
      // Setup mocks for key generation scenario
      Keychain.getInternetCredentials.mockResolvedValue(false);
      PBKDF2.mockResolvedValue('new-encryption-key');
      Keychain.setInternetCredentials.mockResolvedValue(true);

      // Test initialization which should trigger key generation
      await secureStorage.initialize();
      
      expect(PBKDF2).toHaveBeenCalled();
      expect(Keychain.setInternetCredentials).toHaveBeenCalledWith(
        'SecureStorage',
        'encryption_key',
        'new-encryption-key',
        expect.any(Object)
      );
    });
  });

  describe('Migration from AsyncStorage', () => {    it('should handle migration scenarios', async () => {
      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      // Mock a scenario where old AsyncStorage data needs to be migrated
      const legacyData = 'legacy-unencrypted-data';
      const encryptedData = 'encrypted-legacy-data';
      
      AES.encrypt.mockResolvedValue(encryptedData);
      EncryptedStorage.setItem.mockResolvedValue();

      // This would be called during migration
      await secureStorage.setItem('migrated_key', legacyData);
      
      expect(AES.encrypt).toHaveBeenCalled();
      // Check that EncryptedStorage.setItem was called with a JSON structure containing the encrypted data
      expect(EncryptedStorage.setItem).toHaveBeenCalledWith(
        'migrated_key', 
        expect.stringContaining(encryptedData)
      );
    });
  });

  describe('Integration Tests', () => {
    beforeEach(async () => {
      const { PBKDF2 } = require('react-native-aes-crypto');
      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      const Keychain = require('react-native-keychain');
      
      // Setup successful mocks for a clean test environment
      PBKDF2.mockResolvedValue('mock-encryption-key');
      Keychain.getInternetCredentials.mockResolvedValue(false);
      Keychain.setInternetCredentials.mockResolvedValue(true);
      
      // Mock encryption/decryption to return predictable values
      AES.encrypt.mockImplementation((data) => Promise.resolve(`encrypted_${data}`));
      AES.decrypt.mockImplementation((encryptedData) => {
        if (encryptedData.startsWith('encrypted_')) {
          return Promise.resolve(encryptedData.replace('encrypted_', ''));
        }
        return Promise.resolve(encryptedData);
      });
      
      EncryptedStorage.setItem.mockResolvedValue();
      EncryptedStorage.removeItem.mockResolvedValue();
      
      await secureStorage.initialize();
    });

    it('should write "hello world" to secureStorage then read it back with equality', async () => {
      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      const testKey = 'integration_test_key';
      const testValue = 'hello world';
      
      // Mock EncryptedStorage.getItem to return the encrypted structure
      EncryptedStorage.getItem.mockResolvedValue(JSON.stringify({
        iv: 'test-iv',
        data: `encrypted_${testValue}`,
        timestamp: Date.now()
      }));

      // Write the test data
      await secureStorage.setItem(testKey, testValue);
      
      // Verify encryption was called
      expect(AES.encrypt).toHaveBeenCalledWith(testValue, 'mock-encryption-key', expect.any(String), 'aes-256-cbc');
      
      // Read the data back
      const retrievedValue = await secureStorage.getItem(testKey);
      
      // Verify retrieval operations
      expect(EncryptedStorage.getItem).toHaveBeenCalledWith(testKey);
      expect(AES.decrypt).toHaveBeenCalled();
      
      // Assert equality
      expect(retrievedValue).toBe(testValue);
    });

    it('should write dummy JSON, remove it, then assert getItem returns null', async () => {
      const { AES } = require('react-native-aes-crypto');
      const EncryptedStorage = require('react-native-encrypted-storage');
      
      const testKey = 'json_test_key';
      const testData = {
        id: 123,
        name: 'Test Object',
        settings: {
          enabled: true,
          priority: 'high'
        },
        tags: ['test', 'dummy', 'json']
      };
      const testValue = JSON.stringify(testData);
      
      // Step 1: Write the JSON data
      await secureStorage.setItem(testKey, testValue);
      
      // Verify it was stored with encryption
      expect(AES.encrypt).toHaveBeenCalledWith(testValue, 'mock-encryption-key', expect.any(String), 'aes-256-cbc');
      expect(EncryptedStorage.setItem).toHaveBeenCalledWith(testKey, expect.any(String));
      
      // Step 2: Remove the data
      await secureStorage.removeItem(testKey);
      
      // Verify removal was called
      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith(testKey);
      
      // Step 3: Mock EncryptedStorage to return null (item removed)
      EncryptedStorage.getItem.mockResolvedValue(null);
      
      // Step 4: Try to retrieve the removed data
      const result = await secureStorage.getItem(testKey);
      
      // Step 5: Assert getItem returns null
      expect(result).toBeNull();
      expect(EncryptedStorage.getItem).toHaveBeenCalledWith(testKey);
    });
  });
});
