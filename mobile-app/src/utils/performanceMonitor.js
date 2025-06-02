/**
 * Performance Monitoring System
 * Tracks app performance metrics, API response times, and user interactions
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';

class PerformanceMonitor {
  constructor() {
    this.metrics = new Map();
    this.apiMetrics = new Map();
    this.userInteractions = [];
    this.networkMetrics = new Map();
    this.memoryMetrics = [];
    this.isMonitoring = false;
    
    // Performance thresholds
    this.thresholds = {
      apiResponseTime: 5000, // 5 seconds
      screenLoadTime: 3000,  // 3 seconds
      memoryUsage: 512 * 1024 * 1024, // 512MB
      storageUsage: 1024 * 1024 * 1024, // 1GB
    };
    
    this.startMonitoring();
  }

  /**
   * Start performance monitoring
   */
  startMonitoring() {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    console.log('📊 Performance monitoring started');
    
    // Monitor network changes
    this.networkUnsubscribe = NetInfo.addEventListener(state => {
      this.recordNetworkMetric(state);
    });
    
    // Monitor memory usage periodically
    this.memoryInterval = setInterval(() => {
      this.recordMemoryMetric();
    }, 30000); // Every 30 seconds
    
    // Clean up old metrics periodically
    this.cleanupInterval = setInterval(() => {
      this.cleanupOldMetrics();
    }, 300000); // Every 5 minutes
  }

  /**
   * Stop performance monitoring
   */
  stopMonitoring() {
    if (!this.isMonitoring) return;
    
    this.isMonitoring = false;
    console.log('📊 Performance monitoring stopped');
    
    if (this.networkUnsubscribe) {
      this.networkUnsubscribe();
    }
    
    if (this.memoryInterval) {
      clearInterval(this.memoryInterval);
    }
    
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
  }

  /**
   * Record screen load time
   */
  recordScreenLoad(screenName, startTime, endTime = Date.now()) {
    const loadTime = endTime - startTime;
    const metricKey = `screen_load_${screenName}`;
    
    if (!this.metrics.has(metricKey)) {
      this.metrics.set(metricKey, []);
    }
    
    this.metrics.get(metricKey).push({
      timestamp: endTime,
      duration: loadTime,
      screenName,
    });
    
    // Check threshold
    if (loadTime > this.thresholds.screenLoadTime) {
      console.warn(`⚠️ Slow screen load: ${screenName} (${loadTime}ms)`);
      this.recordPerformanceIssue('slow_screen_load', {
        screenName,
        duration: loadTime,
        threshold: this.thresholds.screenLoadTime,
      });
    }
    
    console.log(`📱 Screen load: ${screenName} (${loadTime}ms)`);
  }

  /**
   * Record API call performance
   */
  recordApiCall(endpoint, method, startTime, endTime = Date.now(), status, error = null) {
    const responseTime = endTime - startTime;
    const metricKey = `api_${method}_${endpoint}`;
    
    if (!this.apiMetrics.has(metricKey)) {
      this.apiMetrics.set(metricKey, []);
    }
    
    const metric = {
      timestamp: endTime,
      duration: responseTime,
      endpoint,
      method,
      status,
      error: error ? error.message : null,
    };
    
    this.apiMetrics.get(metricKey).push(metric);
    
    // Check threshold
    if (responseTime > this.thresholds.apiResponseTime) {
      console.warn(`⚠️ Slow API call: ${method} ${endpoint} (${responseTime}ms)`);
      this.recordPerformanceIssue('slow_api_response', {
        endpoint,
        method,
        duration: responseTime,
        threshold: this.thresholds.apiResponseTime,
      });
    }
    
    // Log error
    if (error) {
      console.error(`❌ API error: ${method} ${endpoint}`, error);
      this.recordPerformanceIssue('api_error', {
        endpoint,
        method,
        error: error.message,
        status,
      });
    }
    
    console.log(`🌐 API call: ${method} ${endpoint} (${responseTime}ms) - ${status}`);
  }

  /**
   * Record user interaction
   */
  recordUserInteraction(action, component, metadata = {}) {
    const interaction = {
      timestamp: Date.now(),
      action,
      component,
      metadata,
    };
    
    this.userInteractions.push(interaction);
    
    // Keep only last 100 interactions
    if (this.userInteractions.length > 100) {
      this.userInteractions = this.userInteractions.slice(-100);
    }
    
    console.log(`👆 User interaction: ${action} on ${component}`);
  }

  /**
   * Record network metric
   */
  recordNetworkMetric(networkState) {
    const metric = {
      timestamp: Date.now(),
      type: networkState.type,
      isConnected: networkState.isConnected,
      isInternetReachable: networkState.isInternetReachable,
      details: networkState.details,
    };
    
    if (!this.networkMetrics.has('network_state')) {
      this.networkMetrics.set('network_state', []);
    }
    
    this.networkMetrics.get('network_state').push(metric);
    
    // Log network changes
    if (!networkState.isConnected) {
      console.warn('📡 Network disconnected');
      this.recordPerformanceIssue('network_disconnected', metric);
    } else if (networkState.isConnected && networkState.type !== 'wifi') {
      console.warn(`📡 Network changed to: ${networkState.type}`);
    }
  }

  /**
   * Record memory usage
   */
  recordMemoryMetric() {
    // Note: React Native doesn't provide direct memory access
    // This is a placeholder for native implementation
    const memoryMetric = {
      timestamp: Date.now(),
      // These would be provided by native modules
      usedMemory: 0,
      totalMemory: 0,
      availableMemory: 0,
    };
    
    this.memoryMetrics.push(memoryMetric);
    
    // Keep only last 20 memory metrics (10 minutes)
    if (this.memoryMetrics.length > 20) {
      this.memoryMetrics = this.memoryMetrics.slice(-20);
    }
  }

  /**
   * Record performance issue
   */
  recordPerformanceIssue(type, details) {
    const issue = {
      timestamp: Date.now(),
      type,
      details,
    };
    
    // Store in AsyncStorage for crash recovery
    this.persistPerformanceIssue(issue);
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary() {
    const summary = {
      screens: this.getScreenMetricsSummary(),
      apis: this.getApiMetricsSummary(),
      network: this.getNetworkMetricsSummary(),
      userInteractions: this.userInteractions.length,
      memoryUsage: this.getMemoryUsageSummary(),
      timestamp: Date.now(),
    };
    
    return summary;
  }

  /**
   * Get screen metrics summary
   */
  getScreenMetricsSummary() {
    const summary = {};
    
    for (const [key, metrics] of this.metrics.entries()) {
      if (key.startsWith('screen_load_')) {
        const screenName = key.replace('screen_load_', '');
        const durations = metrics.map(m => m.duration);
        
        summary[screenName] = {
          count: durations.length,
          average: durations.reduce((a, b) => a + b, 0) / durations.length,
          min: Math.min(...durations),
          max: Math.max(...durations),
          recent: durations.slice(-5), // Last 5 loads
        };
      }
    }
    
    return summary;
  }

  /**
   * Get API metrics summary
   */
  getApiMetricsSummary() {
    const summary = {};
    
    for (const [key, metrics] of this.apiMetrics.entries()) {
      const durations = metrics.map(m => m.duration);
      const errors = metrics.filter(m => m.error).length;
      const successRate = ((metrics.length - errors) / metrics.length * 100).toFixed(2);
      
      summary[key] = {
        count: metrics.length,
        average: durations.reduce((a, b) => a + b, 0) / durations.length,
        min: Math.min(...durations),
        max: Math.max(...durations),
        errors,
        successRate: `${successRate}%`,
        recent: metrics.slice(-5), // Last 5 calls
      };
    }
    
    return summary;
  }

  /**
   * Get network metrics summary
   */
  getNetworkMetricsSummary() {
    const networkStates = this.networkMetrics.get('network_state') || [];
    const recentStates = networkStates.slice(-10);
    
    const summary = {
      totalStateChanges: networkStates.length,
      currentState: recentStates[recentStates.length - 1] || null,
      disconnectionEvents: networkStates.filter(s => !s.isConnected).length,
      connectionTypes: {},
    };
    
    // Count connection types
    recentStates.forEach(state => {
      if (state.type) {
        summary.connectionTypes[state.type] = (summary.connectionTypes[state.type] || 0) + 1;
      }
    });
    
    return summary;
  }

  /**
   * Get memory usage summary
   */
  getMemoryUsageSummary() {
    if (this.memoryMetrics.length === 0) {
      return { available: false };
    }
    
    const recent = this.memoryMetrics.slice(-5);
    return {
      available: true,
      recentSamples: recent.length,
      // This would be implemented with native modules
      trend: 'stable', // 'increasing', 'decreasing', 'stable'
    };
  }

  /**
   * Export performance data for analysis
   */
  async exportPerformanceData() {
    const data = {
      summary: this.getPerformanceSummary(),
      rawMetrics: {
        screens: Object.fromEntries(this.metrics),
        apis: Object.fromEntries(this.apiMetrics),
        network: Object.fromEntries(this.networkMetrics),
        memory: this.memoryMetrics,
        userInteractions: this.userInteractions,
      },
      export_timestamp: Date.now(),
      app_version: '1.0.0', // Get from package.json or config
    };
    
    try {
      await AsyncStorage.setItem('@performance_data', JSON.stringify(data));
      console.log('📊 Performance data exported to storage');
      return data;
    } catch (error) {
      console.error('❌ Failed to export performance data:', error);
      throw error;
    }
  }

  /**
   * Clear all performance data
   */
  clearPerformanceData() {
    this.metrics.clear();
    this.apiMetrics.clear();
    this.networkMetrics.clear();
    this.memoryMetrics = [];
    this.userInteractions = [];
    
    AsyncStorage.removeItem('@performance_data');
    AsyncStorage.removeItem('@performance_issues');
    
    console.log('📊 Performance data cleared');
  }

  /**
   * Persist performance issue to storage
   */
  async persistPerformanceIssue(issue) {
    try {
      const existing = await AsyncStorage.getItem('@performance_issues');
      const issues = existing ? JSON.parse(existing) : [];
      
      issues.push(issue);
      
      // Keep only last 50 issues
      if (issues.length > 50) {
        issues.splice(0, issues.length - 50);
      }
      
      await AsyncStorage.setItem('@performance_issues', JSON.stringify(issues));
    } catch (error) {
      console.error('❌ Failed to persist performance issue:', error);
    }
  }

  /**
   * Clean up old metrics
   */
  cleanupOldMetrics() {
    const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours ago
    
    // Clean screen metrics
    for (const [key, metrics] of this.metrics.entries()) {
      const filtered = metrics.filter(m => m.timestamp > cutoffTime);
      this.metrics.set(key, filtered);
    }
    
    // Clean API metrics
    for (const [key, metrics] of this.apiMetrics.entries()) {
      const filtered = metrics.filter(m => m.timestamp > cutoffTime);
      this.apiMetrics.set(key, filtered);
    }
    
    // Clean network metrics
    for (const [key, metrics] of this.networkMetrics.entries()) {
      const filtered = metrics.filter(m => m.timestamp > cutoffTime);
      this.networkMetrics.set(key, filtered);
    }
    
    // Clean user interactions
    this.userInteractions = this.userInteractions.filter(i => i.timestamp > cutoffTime);
    
    console.log('🧹 Old performance metrics cleaned up');
  }
}

// Performance decorators for easy integration
export const withPerformanceTracking = (WrappedComponent, componentName) => {
  return class extends React.Component {
    componentDidMount() {
      const loadTime = Date.now() - this.startTime;
      performanceMonitor.recordScreenLoad(componentName, this.startTime);
    }
    
    componentWillMount() {
      this.startTime = Date.now();
    }
    
    render() {
      return <WrappedComponent {...this.props} />;
    }
  };
};

export const trackApiCall = async (apiCall, endpoint, method = 'GET') => {
  const startTime = Date.now();
  
  try {
    const result = await apiCall();
    performanceMonitor.recordApiCall(endpoint, method, startTime, Date.now(), 'success');
    return result;
  } catch (error) {
    performanceMonitor.recordApiCall(endpoint, method, startTime, Date.now(), 'error', error);
    throw error;
  }
};

// Export singleton instance
const performanceMonitor = new PerformanceMonitor();
export default performanceMonitor;
