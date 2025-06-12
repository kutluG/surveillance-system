import EncryptedStorage from 'react-native-encrypted-storage';
import { AES, SHA256, enc, PBKDF2 } from 'react-native-aes-crypto';
import DeviceInfo from 'react-native-device-info';
import Keychain from 'react-native-keychain';

/**
 * Secure Storage Wrapper with AES-256-CBC Encryption
 * 
 * This module provides encrypted storage for sensitive data like alerts, events,
 * user tokens, and offline cache data. All data is encrypted at rest using
 * AES-256-CBC with keys derived from device-unique identifiers.
 * 
 * Features:
 * - AES-256-CBC encryption for all stored data
 * - PBKDF2 key derivation from device-unique ID
 * - Automatic fallback on decryption failure
 * - Secure key storage in Keychain/Keystore
 */

interface SecureStorageConfig {
  keyDerivationIterations: number;
  saltLength: number;
  ivLength: number;
}

class SecureStorageManager {
  private static instance: SecureStorageManager;
  private encryptionKey: string | null = null;
  private isInitialized: boolean = false;

  private config: SecureStorageConfig = {
    keyDerivationIterations: 10000, // PBKDF2 iterations
    saltLength: 16, // Salt length in bytes
    ivLength: 16, // IV length in bytes
  };

  private constructor() {}

  static getInstance(): SecureStorageManager {
    if (!SecureStorageManager.instance) {
      SecureStorageManager.instance = new SecureStorageManager();
    }
    return SecureStorageManager.instance;
  }

  /**
   * Initialize the secure storage system
   * This should be called on app startup
   */
  async initialize(): Promise<void> {
    try {
      if (this.isInitialized) return;

      // Try to get existing encryption key from keychain
      const existingKey = await this.getStoredEncryptionKey();
      
      if (existingKey) {
        this.encryptionKey = existingKey;
      } else {
        // Generate new encryption key
        this.encryptionKey = await this.generateEncryptionKey();
        await this.storeEncryptionKey(this.encryptionKey);
      }

      this.isInitialized = true;
      console.log('SecureStorage initialized successfully');
    } catch (error) {
      console.error('Failed to initialize SecureStorage:', error);
      throw new Error('SecureStorage initialization failed');
    }
  }

  /**
   * Generate a new encryption key using device-unique ID and PBKDF2
   */
  private async generateEncryptionKey(): Promise<string> {
    try {
      // Get device unique ID
      const deviceId = await DeviceInfo.getUniqueId();
      
      // Generate random salt
      const salt = this.generateRandomBytes(this.config.saltLength);
      
      // Derive key using PBKDF2
      const key = await PBKDF2(
        deviceId,
        salt,
        this.config.keyDerivationIterations,
        32 // 256 bits
      );

      return key;
    } catch (error) {
      console.error('Failed to generate encryption key:', error);
      throw error;
    }
  }

  /**
   * Store encryption key securely in Keychain/Keystore
   */
  private async storeEncryptionKey(key: string): Promise<void> {
    try {
      await Keychain.setInternetCredentials(
        'surveillance_app_encryption_key',
        'encryption',
        key,
        {
          accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET_OR_DEVICE_PASSCODE,
          accessGroup: 'surveillance.app.secure',
        }
      );
    } catch (error) {
      console.error('Failed to store encryption key:', error);
      throw error;
    }
  }

  /**
   * Retrieve encryption key from Keychain/Keystore
   */
  private async getStoredEncryptionKey(): Promise<string | null> {
    try {
      const credentials = await Keychain.getInternetCredentials('surveillance_app_encryption_key');
      
      if (credentials && credentials.password) {
        return credentials.password;
      }
      return null;
    } catch (error) {
      console.warn('Failed to retrieve encryption key:', error);
      return null;
    }
  }

  /**
   * Generate random bytes for salt and IV
   */
  private generateRandomBytes(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  /**
   * Encrypt data using AES-256-CBC
   */
  private async encryptData(data: string): Promise<string> {
    try {
      if (!this.encryptionKey) {
        throw new Error('Encryption key not initialized');
      }

      // Generate random IV
      const iv = this.generateRandomBytes(this.config.ivLength);
      
      // Encrypt data
      const encrypted = await AES.encrypt(data, this.encryptionKey, iv, 'aes-256-cbc');
      
      // Combine IV and encrypted data
      const combined = JSON.stringify({
        iv,
        data: encrypted,
        timestamp: Date.now(),
      });

      return combined;
    } catch (error) {
      console.error('Encryption failed:', error);
      throw error;
    }
  }

  /**
   * Decrypt data using AES-256-CBC
   */
  private async decryptData(encryptedData: string): Promise<string> {
    try {
      if (!this.encryptionKey) {
        throw new Error('Encryption key not initialized');
      }

      // Parse combined data
      const parsed = JSON.parse(encryptedData);
      const { iv, data } = parsed;

      // Decrypt data
      const decrypted = await AES.decrypt(data, this.encryptionKey, iv, 'aes-256-cbc');
      
      return decrypted;
    } catch (error) {
      console.error('Decryption failed:', error);
      throw error;
    }
  }

  /**
   * Store encrypted data
   */
  async setItem(key: string, value: string): Promise<void> {
    try {
      if (!this.isInitialized) {
        await this.initialize();
      }

      const encryptedValue = await this.encryptData(value);
      await EncryptedStorage.setItem(key, encryptedValue);
    } catch (error) {
      console.error(`Failed to set item ${key}:`, error);
      throw error;
    }
  }

  /**
   * Retrieve and decrypt data
   */
  async getItem(key: string): Promise<string | null> {
    try {
      if (!this.isInitialized) {
        await this.initialize();
      }

      const encryptedValue = await EncryptedStorage.getItem(key);
      
      if (!encryptedValue) {
        return null;
      }

      try {
        const decryptedValue = await this.decryptData(encryptedValue);
        return decryptedValue;
      } catch (decryptError) {
        // Fallback: if decryption fails, clear the corrupt data
        console.warn(`Decryption failed for key ${key}, clearing corrupt data:`, decryptError);
        await this.removeItem(key);
        return null;
      }
    } catch (error) {
      console.error(`Failed to get item ${key}:`, error);
      return null;
    }
  }

  /**
   * Remove encrypted data
   */
  async removeItem(key: string): Promise<void> {
    try {
      await EncryptedStorage.removeItem(key);
    } catch (error) {
      console.error(`Failed to remove item ${key}:`, error);
      throw error;
    }
  }

  /**
   * Clear all encrypted storage
   */
  async clear(): Promise<void> {
    try {
      await EncryptedStorage.clear();
    } catch (error) {
      console.error('Failed to clear encrypted storage:', error);
      throw error;
    }
  }

  /**
   * Get all keys from encrypted storage
   */
  async getAllKeys(): Promise<string[]> {
    try {
      return await EncryptedStorage.getAllKeys();
    } catch (error) {
      console.error('Failed to get all keys:', error);
      return [];
    }
  }

  /**
   * Check if secure storage is initialized
   */
  isReady(): boolean {
    return this.isInitialized && this.encryptionKey !== null;
  }

  /**
   * Reset encryption key (use with caution - will invalidate all stored data)
   */
  async resetEncryptionKey(): Promise<void> {
    try {
      // Clear all existing data
      await this.clear();
      
      // Remove old key
      await Keychain.resetInternetCredentials('surveillance_app_encryption_key');
      
      // Generate new key
      this.encryptionKey = await this.generateEncryptionKey();
      await this.storeEncryptionKey(this.encryptionKey);
      
      console.log('Encryption key reset successfully');
    } catch (error) {
      console.error('Failed to reset encryption key:', error);
      throw error;
    }
  }
}

// Export singleton instance
const secureStorage = SecureStorageManager.getInstance();

export default secureStorage;

// Export convenience functions for easier usage
export const setItem = (key: string, value: string): Promise<void> => secureStorage.setItem(key, value);
export const getItem = (key: string): Promise<string | null> => secureStorage.getItem(key);
export const removeItem = (key: string): Promise<void> => secureStorage.removeItem(key);
export const clear = (): Promise<void> => secureStorage.clear();
export const getAllKeys = (): Promise<string[]> => secureStorage.getAllKeys();
export const isReady = (): boolean => secureStorage.isReady();
export const initialize = (): Promise<void> => secureStorage.initialize();
export const resetEncryptionKey = (): Promise<void> => secureStorage.resetEncryptionKey();
