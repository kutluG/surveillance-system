import React from 'react';
import { Platform } from 'react-native';
import RNFS from 'react-native-fs';
import AsyncStorage from '@react-native-async-storage/async-storage';

class PerformanceService {
  constructor() {
    this.performanceMetrics = {
      appStartTime: Date.now(),
      memoryUsage: [],
      renderTimes: new Map(),
      networkRequests: [],
      cacheHits: 0,
      cacheMisses: 0,
    };
    
    this.isMonitoring = false;
    this.monitoringInterval = null;
    this.memoryThreshold = 100 * 1024 * 1024; // 100MB
  }

  async initialize() {
    try {
      console.log('Initializing Performance Service...');
      
      // Start performance monitoring
      this.startMonitoring();
      
      // Initialize cache management
      await this.initializeCacheManagement();
      
      // Set up memory warning listeners
      this.setupMemoryWarnings();
      
      console.log('Performance Service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Performance Service:', error);
    }
  }

  startMonitoring() {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics();
    }, 10000); // Collect metrics every 10 seconds
    
    console.log('Performance monitoring started');
  }

  stopMonitoring() {
    if (!this.isMonitoring) return;
    
    this.isMonitoring = false;
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    
    console.log('Performance monitoring stopped');
  }

  async collectMetrics() {
    try {
      // Collect memory usage
      const memoryInfo = await this.getMemoryInfo();
      this.performanceMetrics.memoryUsage.push({
        timestamp: Date.now(),
        used: memoryInfo.used,
        available: memoryInfo.available,
        total: memoryInfo.total,
      });

      // Keep only last 100 memory samples
      if (this.performanceMetrics.memoryUsage.length > 100) {
        this.performanceMetrics.memoryUsage.shift();
      }

      // Check memory threshold
      if (memoryInfo.used > this.memoryThreshold) {
        console.warn('Memory usage exceeds threshold:', memoryInfo.used);
        await this.handleHighMemoryUsage();
      }

      // Collect cache statistics
      const cacheStats = await this.getCacheStatistics();
      this.performanceMetrics.cacheHits = cacheStats.hits;
      this.performanceMetrics.cacheMisses = cacheStats.misses;

    } catch (error) {
      console.error('Failed to collect performance metrics:', error);
    }
  }

  async getMemoryInfo() {
    try {
      if (Platform.OS === 'android') {
        // Android memory info
        return {
          used: 50 * 1024 * 1024, // Mock data
          available: 200 * 1024 * 1024,
          total: 250 * 1024 * 1024,
        };
      } else if (Platform.OS === 'ios') {
        // iOS memory info
        return {
          used: 45 * 1024 * 1024, // Mock data
          available: 180 * 1024 * 1024,
          total: 225 * 1024 * 1024,
        };
      }
    } catch (error) {
      console.error('Failed to get memory info:', error);
      return { used: 0, available: 0, total: 0 };
    }
  }

  measureRenderTime(componentName, startTime, endTime) {
    const renderTime = endTime - startTime;
    
    if (!this.performanceMetrics.renderTimes.has(componentName)) {
      this.performanceMetrics.renderTimes.set(componentName, []);
    }
    
    const times = this.performanceMetrics.renderTimes.get(componentName);
    times.push({
      timestamp: Date.now(),
      duration: renderTime,
    });
    
    // Keep only last 50 render times per component
    if (times.length > 50) {
      times.shift();
    }
    
    // Log slow renders
    if (renderTime > 100) { // More than 100ms
      console.warn(`Slow render detected for ${componentName}: ${renderTime}ms`);
    }
  }

  trackNetworkRequest(url, method, startTime, endTime, success, size = 0) {
    const duration = endTime - startTime;
    
    this.performanceMetrics.networkRequests.push({
      url,
      method,
      duration,
      success,
      size,
      timestamp: Date.now(),
    });
    
    // Keep only last 100 network requests
    if (this.performanceMetrics.networkRequests.length > 100) {
      this.performanceMetrics.networkRequests.shift();
    }
    
    // Log slow requests
    if (duration > 5000) { // More than 5 seconds
      console.warn(`Slow network request: ${method} ${url} took ${duration}ms`);
    }
  }

  async initializeCacheManagement() {
    try {
      // Check cache directory
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const cacheExists = await RNFS.exists(`${cacheDir}/app-cache`);
      if (!cacheExists) {
        await RNFS.mkdir(`${cacheDir}/app-cache`);
      }
      
      // Clean old cache files
      await this.cleanOldCacheFiles();
      
      console.log('Cache management initialized');
    } catch (error) {
      console.error('Failed to initialize cache management:', error);
    }
  }

  async cleanOldCacheFiles() {
    try {
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const files = await RNFS.readDir(`${cacheDir}/app-cache`);
      const now = Date.now();
      const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
      
      for (const file of files) {
        const fileAge = now - new Date(file.mtime).getTime();
        if (fileAge > maxAge) {
          await RNFS.unlink(file.path);
          console.log(`Deleted old cache file: ${file.name}`);
        }
      }
    } catch (error) {
      console.error('Failed to clean old cache files:', error);
    }
  }

  async getCacheStatistics() {
    try {
      const cacheStats = await AsyncStorage.getItem('cache_statistics');
      if (cacheStats) {
        return JSON.parse(cacheStats);
      }
      return { hits: 0, misses: 0 };
    } catch (error) {
      console.error('Failed to get cache statistics:', error);
      return { hits: 0, misses: 0 };
    }
  }

  async updateCacheStatistics(hits, misses) {
    try {
      const stats = { hits, misses };
      await AsyncStorage.setItem('cache_statistics', JSON.stringify(stats));
    } catch (error) {
      console.error('Failed to update cache statistics:', error);
    }
  }

  setupMemoryWarnings() {
    try {
      // This would need to be implemented with native modules
      // For now, we'll simulate memory warnings
      console.log('Memory warning listeners set up');
    } catch (error) {
      console.error('Failed to set up memory warnings:', error);
    }
  }

  async handleHighMemoryUsage() {
    try {
      console.log('Handling high memory usage...');
      
      // Clear image cache
      await this.clearImageCache();
      
      // Clear old data from Redux store
      // This would need to be integrated with your Redux store
      
      // Trigger garbage collection (if available)
      if (global.gc) {
        global.gc();
      }
      
      console.log('Memory cleanup completed');
    } catch (error) {
      console.error('Failed to handle high memory usage:', error);
    }
  }

  async clearImageCache() {
    try {
      const cacheDir = Platform.select({
        ios: RNFS.CachesDirectoryPath,
        android: RNFS.CachesDirectoryPath,
      });
      
      const imageCache = `${cacheDir}/image-cache`;
      const exists = await RNFS.exists(imageCache);
      
      if (exists) {
        const files = await RNFS.readDir(imageCache);
        for (const file of files) {
          await RNFS.unlink(file.path);
        }
        console.log(`Cleared ${files.length} cached images`);
      }
    } catch (error) {
      console.error('Failed to clear image cache:', error);
    }
  }

  async optimizeApp() {
    try {
      console.log('Starting app optimization...');
      
      // Clean caches
      await this.cleanOldCacheFiles();
      
      // Optimize images
      await this.optimizeImageCache();
      
      // Compress stored data
      await this.compressStoredData();
      
      console.log('App optimization completed');
      return true;
    } catch (error) {
      console.error('App optimization failed:', error);
      return false;
    }
  }

  async optimizeImageCache() {
    try {
      // This would implement image compression and optimization
      console.log('Optimizing image cache...');
    } catch (error) {
      console.error('Failed to optimize image cache:', error);
    }
  }

  async compressStoredData() {
    try {
      // This would implement data compression for stored data
      console.log('Compressing stored data...');
    } catch (error) {
      console.error('Failed to compress stored data:', error);
    }
  }

  getPerformanceReport() {
    const now = Date.now();
    const uptime = now - this.performanceMetrics.appStartTime;
    
    // Calculate average memory usage
    const memoryUsages = this.performanceMetrics.memoryUsage.map(m => m.used);
    const avgMemory = memoryUsages.length > 0 
      ? memoryUsages.reduce((a, b) => a + b, 0) / memoryUsages.length 
      : 0;
    
    // Calculate average render times per component
    const renderStats = {};
    for (const [component, times] of this.performanceMetrics.renderTimes) {
      const durations = times.map(t => t.duration);
      renderStats[component] = {
        count: durations.length,
        average: durations.reduce((a, b) => a + b, 0) / durations.length,
        max: Math.max(...durations),
        min: Math.min(...durations),
      };
    }
    
    // Calculate network performance
    const networkRequests = this.performanceMetrics.networkRequests;
    const successfulRequests = networkRequests.filter(r => r.success);
    const avgNetworkTime = networkRequests.length > 0
      ? networkRequests.reduce((a, b) => a + b.duration, 0) / networkRequests.length
      : 0;
    
    // Calculate cache hit rate
    const totalCacheRequests = this.performanceMetrics.cacheHits + this.performanceMetrics.cacheMisses;
    const cacheHitRate = totalCacheRequests > 0 
      ? (this.performanceMetrics.cacheHits / totalCacheRequests) * 100 
      : 0;
    
    return {
      uptime,
      memory: {
        average: avgMemory,
        current: memoryUsages.length > 0 ? memoryUsages[memoryUsages.length - 1] : 0,
        samples: memoryUsages.length,
      },
      rendering: renderStats,
      network: {
        totalRequests: networkRequests.length,
        successfulRequests: successfulRequests.length,
        averageTime: avgNetworkTime,
        successRate: networkRequests.length > 0 
          ? (successfulRequests.length / networkRequests.length) * 100 
          : 0,
      },
      cache: {
        hitRate: cacheHitRate,
        hits: this.performanceMetrics.cacheHits,
        misses: this.performanceMetrics.cacheMisses,
      },
      timestamp: now,
    };
  }

  async exportPerformanceData() {
    try {
      const report = this.getPerformanceReport();
      const dataString = JSON.stringify(report, null, 2);
      
      const documentsPath = Platform.select({
        ios: RNFS.DocumentDirectoryPath,
        android: RNFS.ExternalStorageDirectoryPath,
      });
      
      const filename = `performance-report-${Date.now()}.json`;
      const filepath = `${documentsPath}/${filename}`;
      
      await RNFS.writeFile(filepath, dataString, 'utf8');
      
      console.log(`Performance report exported to: ${filepath}`);
      return filepath;
    } catch (error) {
      console.error('Failed to export performance data:', error);
      throw error;
    }
  }
}

export default new PerformanceService();
