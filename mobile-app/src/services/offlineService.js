import React from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import RNFS from 'react-native-fs';
import NetInfo from '@react-native-netinfo/netinfo';

class OfflineService {
  constructor() {
    this.isOffline = false;
    this.pendingRequests = [];
    this.offlineData = new Map();
    this.syncQueue = [];
    this.maxOfflineStorageSize = 50 * 1024 * 1024; // 50MB
    this.isInitialized = false;
  }

  async initialize() {
    try {
      console.log('Initializing Offline Service...');
      
      // Set up network state monitoring
      await this.setupNetworkMonitoring();
      
      // Load offline data from storage
      await this.loadOfflineData();
      
      // Load pending sync queue
      await this.loadSyncQueue();
      
      // Set up periodic sync attempts
      this.setupPeriodicSync();
      
      this.isInitialized = true;
      console.log('Offline Service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Offline Service:', error);
      throw error;
    }
  }

  async setupNetworkMonitoring() {
    try {
      // Get initial network state
      const networkState = await NetInfo.fetch();
      this.isOffline = !networkState.isConnected;
      
      // Listen for network state changes
      NetInfo.addEventListener(state => {
        const wasOffline = this.isOffline;
        this.isOffline = !state.isConnected;
        
        if (wasOffline && !this.isOffline) {
          // Came back online, start syncing
          console.log('Network connection restored, starting sync...');
          this.startSync();
        } else if (!wasOffline && this.isOffline) {
          // Went offline
          console.log('Network connection lost, entering offline mode...');
        }
      });
      
      console.log('Network monitoring set up, offline:', this.isOffline);
    } catch (error) {
      console.error('Failed to set up network monitoring:', error);
    }
  }

  async loadOfflineData() {
    try {
      const offlineDataString = await AsyncStorage.getItem('offline_data');
      if (offlineDataString) {
        const data = JSON.parse(offlineDataString);
        this.offlineData = new Map(Object.entries(data));
        console.log(`Loaded ${this.offlineData.size} offline data entries`);
      }
    } catch (error) {
      console.error('Failed to load offline data:', error);
    }
  }

  async saveOfflineData() {
    try {
      const dataObject = Object.fromEntries(this.offlineData);
      await AsyncStorage.setItem('offline_data', JSON.stringify(dataObject));
    } catch (error) {
      console.error('Failed to save offline data:', error);
    }
  }

  async loadSyncQueue() {
    try {
      const syncQueueString = await AsyncStorage.getItem('sync_queue');
      if (syncQueueString) {
        this.syncQueue = JSON.parse(syncQueueString);
        console.log(`Loaded ${this.syncQueue.length} pending sync items`);
      }
    } catch (error) {
      console.error('Failed to load sync queue:', error);
    }
  }

  async saveSyncQueue() {
    try {
      await AsyncStorage.setItem('sync_queue', JSON.stringify(this.syncQueue));
    } catch (error) {
      console.error('Failed to save sync queue:', error);
    }
  }

  setupPeriodicSync() {
    // Attempt to sync every 30 seconds when online
    setInterval(() => {
      if (!this.isOffline && this.syncQueue.length > 0) {
        this.startSync();
      }
    }, 30000);
  }

  async cacheData(key, data, expirationTime = 24 * 60 * 60 * 1000) { // 24 hours default
    try {
      const cacheEntry = {
        data,
        timestamp: Date.now(),
        expirationTime,
      };
      
      this.offlineData.set(key, cacheEntry);
      await this.saveOfflineData();
      
      // Check storage size and cleanup if needed
      await this.cleanupOldData();
      
      console.log(`Cached data for key: ${key}`);
    } catch (error) {
      console.error('Failed to cache data:', error);
    }
  }

  getCachedData(key) {
    try {
      const cacheEntry = this.offlineData.get(key);
      
      if (!cacheEntry) {
        return null;
      }
      
      // Check if data has expired
      const now = Date.now();
      if (now - cacheEntry.timestamp > cacheEntry.expirationTime) {
        this.offlineData.delete(key);
        this.saveOfflineData();
        return null;
      }
      
      console.log(`Retrieved cached data for key: ${key}`);
      return cacheEntry.data;
    } catch (error) {
      console.error('Failed to get cached data:', error);
      return null;
    }
  }

  async addToSyncQueue(request) {
    try {
      const syncItem = {
        id: Date.now().toString(),
        request,
        timestamp: Date.now(),
        retryCount: 0,
        maxRetries: 3,
      };
      
      this.syncQueue.push(syncItem);
      await this.saveSyncQueue();
      
      console.log(`Added request to sync queue: ${request.method} ${request.url}`);
      
      // Try to sync immediately if online
      if (!this.isOffline) {
        this.startSync();
      }
    } catch (error) {
      console.error('Failed to add to sync queue:', error);
    }
  }

  async startSync() {
    if (this.isOffline || this.syncQueue.length === 0) {
      return;
    }
    
    console.log(`Starting sync of ${this.syncQueue.length} items...`);
    
    const itemsToSync = [...this.syncQueue];
    const successfulItems = [];
    const failedItems = [];
    
    for (const item of itemsToSync) {
      try {
        await this.syncItem(item);
        successfulItems.push(item);
        console.log(`Successfully synced item: ${item.id}`);
      } catch (error) {
        console.error(`Failed to sync item ${item.id}:`, error);
        
        item.retryCount++;
        if (item.retryCount < item.maxRetries) {
          failedItems.push(item);
        } else {
          console.warn(`Max retries reached for item ${item.id}, removing from queue`);
        }
      }
    }
    
    // Update sync queue
    this.syncQueue = failedItems;
    await this.saveSyncQueue();
    
    console.log(`Sync completed: ${successfulItems.length} successful, ${failedItems.length} failed`);
  }

  async syncItem(item) {
    const { request } = item;
    
    const response = await fetch(request.url, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });
    
    if (!response.ok) {
      throw new Error(`Sync failed: ${response.status} ${response.statusText}`);
    }
    
    return response;
  }

  async cleanupOldData() {
    try {
      // Calculate current storage size
      const currentSize = await this.calculateStorageSize();
      
      if (currentSize > this.maxOfflineStorageSize) {
        console.log('Storage size exceeded, cleaning up old data...');
        
        // Sort by timestamp (oldest first)
        const entries = Array.from(this.offlineData.entries()).sort(
          (a, b) => a[1].timestamp - b[1].timestamp
        );
        
        // Remove oldest entries until we're under the limit
        let removedSize = 0;
        const targetSize = this.maxOfflineStorageSize * 0.8; // Remove until 80% of limit
        
        for (const [key, entry] of entries) {
          this.offlineData.delete(key);
          removedSize += JSON.stringify(entry).length;
          
          if (currentSize - removedSize < targetSize) {
            break;
          }
        }
        
        await this.saveOfflineData();
        console.log(`Cleaned up ${removedSize} bytes of old data`);
      }
    } catch (error) {
      console.error('Failed to cleanup old data:', error);
    }
  }

  async calculateStorageSize() {
    try {
      const dataString = JSON.stringify(Object.fromEntries(this.offlineData));
      return new Blob([dataString]).size;
    } catch (error) {
      console.error('Failed to calculate storage size:', error);
      return 0;
    }
  }

  async cacheVideoThumbnail(videoId, thumbnailUrl) {
    try {
      if (this.isOffline) {
        return this.getCachedVideoThumbnail(videoId);
      }
      
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const thumbnailDir = `${cacheDir}/video-thumbnails`;
      const thumbnailPath = `${thumbnailDir}/${videoId}.jpg`;
      
      // Create directory if it doesn't exist
      const dirExists = await RNFS.exists(thumbnailDir);
      if (!dirExists) {
        await RNFS.mkdir(thumbnailDir);
      }
      
      // Download and cache thumbnail
      const downloadResult = await RNFS.downloadFile({
        fromUrl: thumbnailUrl,
        toFile: thumbnailPath,
      }).promise;
      
      if (downloadResult.statusCode === 200) {
        console.log(`Cached video thumbnail: ${videoId}`);
        return `file://${thumbnailPath}`;
      } else {
        throw new Error(`Download failed with status: ${downloadResult.statusCode}`);
      }
    } catch (error) {
      console.error('Failed to cache video thumbnail:', error);
      return thumbnailUrl; // Return original URL as fallback
    }
  }

  async getCachedVideoThumbnail(videoId) {
    try {
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const thumbnailPath = `${cacheDir}/video-thumbnails/${videoId}.jpg`;
      const exists = await RNFS.exists(thumbnailPath);
      
      if (exists) {
        return `file://${thumbnailPath}`;
      }
      
      return null;
    } catch (error) {
      console.error('Failed to get cached video thumbnail:', error);
      return null;
    }
  }

  async getOfflineCameras() {
    return this.getCachedData('cameras') || [];
  }

  async getOfflineAlerts() {
    return this.getCachedData('alerts') || [];
  }

  async getOfflineRecordings() {
    return this.getCachedData('recordings') || [];
  }

  async cacheImportantData(cameras, alerts, recordings) {
    try {
      await Promise.all([
        this.cacheData('cameras', cameras),
        this.cacheData('alerts', alerts),
        this.cacheData('recordings', recordings),
      ]);
      
      console.log('Important data cached for offline use');
    } catch (error) {
      console.error('Failed to cache important data:', error);
    }
  }

  isOnline() {
    return !this.isOffline;
  }

  isOfflineMode() {
    return this.isOffline;
  }

  getSyncQueueSize() {
    return this.syncQueue.length;
  }

  async clearOfflineData() {
    try {
      this.offlineData.clear();
      this.syncQueue = [];
      
      await Promise.all([
        this.saveOfflineData(),
        this.saveSyncQueue(),
      ]);
      
      // Clear cached files
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const thumbnailDir = `${cacheDir}/video-thumbnails`;
      const dirExists = await RNFS.exists(thumbnailDir);
      if (dirExists) {
        await RNFS.unlink(thumbnailDir);
      }
      
      console.log('All offline data cleared');
    } catch (error) {
      console.error('Failed to clear offline data:', error);
    }
  }

  getOfflineStatus() {
    return {
      isOffline: this.isOffline,
      cachedDataCount: this.offlineData.size,
      syncQueueSize: this.syncQueue.length,
      isInitialized: this.isInitialized,
    };
  }
}

export default new OfflineService();
