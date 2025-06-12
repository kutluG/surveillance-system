import NetInfo from '@react-native-community/netinfo';
import { storeOfflineData } from '../contexts/NetworkProvider';
import secureStorage from '../utils/secureStorage';
import { cameraService } from './cameraService';
import { alertService } from './alertService';

export interface CachedData {
  data: any;
  timestamp: string;
  expiry?: string;
}

export interface ApiRequestConfig {
  cacheKey?: string;
  cacheDuration?: number; // in milliseconds
  offlineSupport?: boolean;
  retryOnReconnect?: boolean;
}

class OfflineApiService {
  private static instance: OfflineApiService;
  private offlineQueue: any[] = [];
  private readonly CACHE_PREFIX = 'api_cache_';
  private readonly OFFLINE_QUEUE_KEY = 'offline_queue';
  private readonly DEFAULT_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  static getInstance(): OfflineApiService {
    if (!OfflineApiService.instance) {
      OfflineApiService.instance = new OfflineApiService();
    }
    return OfflineApiService.instance;
  }

  constructor() {
    this.loadOfflineQueue();
    this.setupNetworkListener();
  }
  private async loadOfflineQueue() {
    try {
      const queueData = await secureStorage.getItem(this.OFFLINE_QUEUE_KEY);
      this.offlineQueue = queueData ? JSON.parse(queueData) : [];
    } catch (error) {
      console.error('Error loading offline queue:', error);
      this.offlineQueue = [];
    }
  }
  private async saveOfflineQueue() {
    try {
      await secureStorage.setItem(this.OFFLINE_QUEUE_KEY, JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.error('Error saving offline queue:', error);
    }
  }

  private setupNetworkListener() {
    NetInfo.addEventListener(state => {
      if (state.isConnected && this.offlineQueue.length > 0) {
        this.processOfflineQueue();
      }
    });
  }

  private async processOfflineQueue() {
    console.log(`Processing ${this.offlineQueue.length} queued requests...`);
    
    const queue = [...this.offlineQueue];
    this.offlineQueue = [];
    await this.saveOfflineQueue();

    for (const request of queue) {
      try {
        console.log(`Retrying ${request.method} ${request.url}`);
        // Execute the original request function
        if (request.retryFunction) {
          await request.retryFunction();
        }
      } catch (error) {
        console.error('Error processing queued request:', error);
        // Re-queue if it's a temporary error
        if (this.isRetryableError(error)) {
          this.offlineQueue.push(request);
        }
      }
    }

    if (this.offlineQueue.length > 0) {
      await this.saveOfflineQueue();
    }
  }

  private isRetryableError(error: any): boolean {
    // Define which errors should trigger a retry
    const retryableCodes = [408, 429, 500, 502, 503, 504];
    return error.response && retryableCodes.includes(error.response.status);
  }
  async getCachedData(key: string): Promise<CachedData | null> {
    try {
      const cachedData = await secureStorage.getItem(this.CACHE_PREFIX + key);
      if (!cachedData) return null;

      const parsed: CachedData = JSON.parse(cachedData);
      
      // Check if data has expired
      if (parsed.expiry && new Date() > new Date(parsed.expiry)) {
        await secureStorage.removeItem(this.CACHE_PREFIX + key);
        return null;
      }

      return parsed;
    } catch (error) {
      console.error('Error getting cached data:', error);
      return null;
    }
  }
  async setCachedData(key: string, data: any, duration?: number): Promise<void> {
    try {
      const cacheDuration = duration || this.DEFAULT_CACHE_DURATION;
      const expiry = new Date(Date.now() + cacheDuration).toISOString();
      
      const cacheData: CachedData = {
        data,
        timestamp: new Date().toISOString(),
        expiry,
      };

      await secureStorage.setItem(this.CACHE_PREFIX + key, JSON.stringify(cacheData));
    } catch (error) {
      console.error('Error setting cached data:', error);
    }
  }

  async makeRequest<T>(
    requestFunction: () => Promise<T>,
    config: ApiRequestConfig = {}
  ): Promise<T> {
    const isOnline = await NetInfo.fetch().then(state => Boolean(state.isConnected));
    
    // Try to get cached data if available
    if (config.cacheKey) {
      const cachedData = await this.getCachedData(config.cacheKey);
      if (cachedData) {
        console.log(`Using cached data for ${config.cacheKey}`);
        return cachedData.data as T;
      }
    }

    if (!isOnline) {
      if (config.offlineSupport) {
        // Queue the request for later execution
        const queuedRequest = {
          timestamp: new Date().toISOString(),
          retryFunction: config.retryOnReconnect ? requestFunction : null,
          config,
        };
        
        this.offlineQueue.push(queuedRequest);
        await this.saveOfflineQueue();
        
        throw new Error('Device is offline. Request queued for later execution.');
      } else {
        throw new Error('Device is offline and request does not support offline mode.');
      }
    }

    try {
      const response = await requestFunction();
      
      // Cache the response if caching is enabled
      if (config.cacheKey) {
        await this.setCachedData(config.cacheKey, response, config.cacheDuration);
      }
      
      return response;
    } catch (error) {
      // If request fails and we have cached data, return it as fallback
      if (config.cacheKey) {
        const cachedData = await this.getCachedData(config.cacheKey);
        if (cachedData) {
          console.log(`Using stale cached data for ${config.cacheKey} due to request failure`);
          return cachedData.data as T;
        }
      }
      
      throw error;
    }
  }
  async clearCache(keyPattern?: string): Promise<void> {
    try {
      const keys = await secureStorage.getAllKeys();
      const cacheKeys = keys.filter(key => {
        if (!key.startsWith(this.CACHE_PREFIX)) return false;
        if (keyPattern) {
          return key.includes(keyPattern);
        }
        return true;
      });
      
      // Clear each key individually since secureStorage doesn't have multiRemove
      for (const key of cacheKeys) {
        await secureStorage.removeItem(key);
      }
      console.log(`Cleared ${cacheKeys.length} cached items`);
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  }

  async getQueueStatus(): Promise<{ queueLength: number; lastProcessed?: string }> {
    return {
      queueLength: this.offlineQueue.length,
      lastProcessed: this.offlineQueue.length > 0 ? this.offlineQueue[0].timestamp : undefined,
    };
  }
  // Enhanced camera service methods with offline support
  async getCameras(params: any = {}) {
    return this.makeRequest(
      () => cameraService.getCameras(params),
      {
        cacheKey: `cameras_${JSON.stringify(params)}`,
        cacheDuration: 2 * 60 * 1000, // 2 minutes
        offlineSupport: true,
        retryOnReconnect: true,
      }
    );
  }

  async getCameraDetails(cameraId: string) {
    return this.makeRequest(
      () => cameraService.getCameraDetails(cameraId),
      {
        cacheKey: `camera_details_${cameraId}`,
        cacheDuration: 5 * 60 * 1000, // 5 minutes
        offlineSupport: true,
        retryOnReconnect: true,
      }
    );
  }

  async getAlerts(params: any = {}) {
    return this.makeRequest(
      () => alertService.getAlerts(params),
      {
        cacheKey: `alerts_${JSON.stringify(params)}`,
        cacheDuration: 1 * 60 * 1000, // 1 minute
        offlineSupport: true,
        retryOnReconnect: true,
      }
    );
  }
  // Methods that require online connectivity (no offline support)
  async updateCameraSettings(cameraId: string, settings: any) {
    return this.makeRequest(
      () => cameraService.updateCameraSettings?.(cameraId, settings),
      {
        offlineSupport: false, // Settings updates require real-time connectivity
      }
    );
  }

  async acknowledgeAlert(alertId: string) {
    return this.makeRequest(
      async () => {
        const result = await alertService.acknowledgeAlert?.(alertId);
        
        // Clear related cache after successful update
        await this.clearCache('alerts_');
        
        return result;
      },
      {
        offlineSupport: true,
        retryOnReconnect: true,
      }
    );
  }
}

export const offlineApiService = OfflineApiService.getInstance();
export default offlineApiService;
