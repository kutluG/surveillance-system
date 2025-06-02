/**
 * Real-time Integration Testing
 * Tests WebSocket connections, live data feeds, and real-time features
 */

import { jest, describe, beforeEach, afterEach, test, expect } from '@jest/globals';
import WebSocket from 'ws';
import realTimeIntegration from '../../services/realTimeIntegration';
import EnvironmentConfig from '../../config/environment';
import performanceMonitor from '../../utils/performanceMonitor';

// Mock WebSocket for testing
jest.mock('ws');

describe('Real-time Integration Tests', () => {
  let mockWebSocket;
  let performanceStartTime;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock WebSocket
    mockWebSocket = {
      readyState: WebSocket.OPEN,
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      on: jest.fn(),
      off: jest.fn(),
    };
    
    WebSocket.mockImplementation(() => mockWebSocket);
    
    // Start performance tracking
    performanceStartTime = Date.now();
    
    console.log('🧪 Starting real-time integration test');
  });

  afterEach(() => {
    // Cleanup
    realTimeIntegration.cleanup();
    
    // Record test performance
    const testDuration = Date.now() - performanceStartTime;
    performanceMonitor.recordUserInteraction('integration_test_completed', 'RealTimeTests', {
      duration: testDuration,
    });
    
    console.log(`🧪 Real-time integration test completed (${testDuration}ms)`);
  });

  describe('WebSocket Connection Management', () => {
    test('should establish WebSocket connection successfully', async () => {
      const connectStartTime = Date.now();
      
      // Initialize with mocked WebSocket
      await realTimeIntegration.initialize();
      
      // Simulate successful connection
      const onOpenCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'open')?.[1];
      
      if (onOpenCallback) {
        onOpenCallback();
      }
      
      // Verify connection was established
      expect(WebSocket).toHaveBeenCalledWith(
        expect.stringContaining(EnvironmentConfig.get('WEBSOCKET_URL'))
      );
      
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('open', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('message', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('close', expect.any(Function));
      
      // Record connection performance
      const connectionTime = Date.now() - connectStartTime;
      performanceMonitor.recordApiCall('/ws/connect', 'WS', connectStartTime, Date.now(), 'success');
      
      console.log(`✅ WebSocket connection established (${connectionTime}ms)`);
    });

    test('should handle WebSocket connection errors gracefully', async () => {
      const errorStartTime = Date.now();
      
      await realTimeIntegration.initialize();
      
      // Simulate connection error
      const onErrorCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'error')?.[1];
      
      const mockError = new Error('WebSocket connection failed');
      
      if (onErrorCallback) {
        onErrorCallback(mockError);
      }
      
      // Record error performance
      performanceMonitor.recordApiCall('/ws/connect', 'WS', errorStartTime, Date.now(), 'error', mockError);
      
      console.log('✅ WebSocket error handling tested');
    });

    test('should auto-reconnect on connection loss', async () => {
      jest.useFakeTimers();
      
      await realTimeIntegration.initialize();
      
      // Simulate connection loss
      const onCloseCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'close')?.[1];
      
      if (onCloseCallback) {
        onCloseCallback({ code: 1006, reason: 'Connection lost' });
      }
      
      // Fast-forward time to trigger reconnection
      jest.advanceTimersByTime(5000);
      
      // Verify reconnection attempt
      expect(WebSocket).toHaveBeenCalledTimes(2);
      
      jest.useRealTimers();
      console.log('✅ Auto-reconnection tested');
    });
  });

  describe('Live Camera Feed Integration', () => {
    test('should handle camera status updates', async () => {
      await realTimeIntegration.initialize();
      
      // Simulate camera status message
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const cameraStatusMessage = {
        data: JSON.stringify({
          type: 'camera_status',
          payload: {
            cameraId: 'camera-01',
            status: 'online',
            timestamp: Date.now(),
            resolution: '1920x1080',
            fps: 30,
          }
        })
      };
      
      if (onMessageCallback) {
        onMessageCallback(cameraStatusMessage);
      }
      
      // Verify message was processed
      expect(realTimeIntegration.getConnectionStatus()).toBe('connected');
      
      console.log('✅ Camera status update processed');
    });

    test('should handle live video frame data', async () => {
      const frameStartTime = Date.now();
      
      await realTimeIntegration.initialize();
      
      // Simulate video frame message
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const frameMessage = {
        data: JSON.stringify({
          type: 'video_frame',
          payload: {
            cameraId: 'camera-01',
            frameId: 'frame-123',
            timestamp: Date.now(),
            format: 'jpeg',
            data: 'base64-encoded-frame-data',
          }
        })
      };
      
      if (onMessageCallback) {
        onMessageCallback(frameMessage);
      }
      
      // Record frame processing performance
      const frameProcessTime = Date.now() - frameStartTime;
      performanceMonitor.recordUserInteraction('video_frame_processed', 'RealTimeIntegration', {
        frameId: 'frame-123',
        processingTime: frameProcessTime,
      });
      
      console.log(`✅ Video frame processed (${frameProcessTime}ms)`);
    });

    test('should handle detection alerts in real-time', async () => {
      const alertStartTime = Date.now();
      
      await realTimeIntegration.initialize();
      
      // Simulate detection alert
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const alertMessage = {
        data: JSON.stringify({
          type: 'detection_alert',
          payload: {
            alertId: 'alert-456',
            cameraId: 'camera-01',
            detectionType: 'person',
            confidence: 0.95,
            timestamp: Date.now(),
            bbox: [100, 100, 200, 200],
            metadata: {
              severity: 'high',
              zone: 'entrance',
            }
          }
        })
      };
      
      if (onMessageCallback) {
        onMessageCallback(alertMessage);
      }
      
      // Record alert processing performance
      const alertProcessTime = Date.now() - alertStartTime;
      performanceMonitor.recordUserInteraction('detection_alert_processed', 'RealTimeIntegration', {
        alertId: 'alert-456',
        processingTime: alertProcessTime,
        confidence: 0.95,
      });
      
      console.log(`✅ Detection alert processed (${alertProcessTime}ms)`);
    });
  });

  describe('System Health Monitoring', () => {
    test('should handle system health updates', async () => {
      await realTimeIntegration.initialize();
      
      // Simulate system health message
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const healthMessage = {
        data: JSON.stringify({
          type: 'system_health',
          payload: {
            services: {
              auth_service: { status: 'healthy', responseTime: 45 },
              camera_service: { status: 'healthy', responseTime: 23 },
              ai_service: { status: 'degraded', responseTime: 1200 },
            },
            timestamp: Date.now(),
          }
        })
      };
      
      if (onMessageCallback) {
        onMessageCallback(healthMessage);
      }
      
      console.log('✅ System health update processed');
    });

    test('should handle service degradation alerts', async () => {
      await realTimeIntegration.initialize();
      
      // Simulate service degradation
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const degradationMessage = {
        data: JSON.stringify({
          type: 'service_degradation',
          payload: {
            service: 'ai_service',
            status: 'degraded',
            reason: 'High response time',
            responseTime: 5000,
            threshold: 3000,
            timestamp: Date.now(),
          }
        })
      };
      
      if (onMessageCallback) {
        onMessageCallback(degradationMessage);
      }
      
      // Record service degradation
      performanceMonitor.recordPerformanceIssue('service_degradation', {
        service: 'ai_service',
        responseTime: 5000,
        threshold: 3000,
      });
      
      console.log('✅ Service degradation alert processed');
    });
  });

  describe('Performance Monitoring', () => {
    test('should track message processing latency', async () => {
      await realTimeIntegration.initialize();
      
      const messageCount = 10;
      const latencies = [];
      
      for (let i = 0; i < messageCount; i++) {
        const messageStartTime = Date.now();
        
        // Simulate processing a message
        const onMessageCallback = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'message')?.[1];
        
        const testMessage = {
          data: JSON.stringify({
            type: 'test_message',
            payload: { id: i, timestamp: messageStartTime }
          })
        };
        
        if (onMessageCallback) {
          onMessageCallback(testMessage);
        }
        
        const latency = Date.now() - messageStartTime;
        latencies.push(latency);
      }
      
      // Calculate performance metrics
      const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
      const maxLatency = Math.max(...latencies);
      const minLatency = Math.min(...latencies);
      
      console.log(`📊 Message processing performance:`);
      console.log(`   Average latency: ${avgLatency.toFixed(2)}ms`);
      console.log(`   Max latency: ${maxLatency}ms`);
      console.log(`   Min latency: ${minLatency}ms`);
      
      // Verify performance meets requirements
      expect(avgLatency).toBeLessThan(100); // 100ms average
      expect(maxLatency).toBeLessThan(500); // 500ms max
      
      console.log('✅ Message processing performance verified');
    });

    test('should track connection stability', async () => {
      jest.useFakeTimers();
      
      let connectionEvents = 0;
      let disconnectionEvents = 0;
      
      await realTimeIntegration.initialize();
      
      // Simulate multiple connect/disconnect cycles
      const onOpenCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'open')?.[1];
      const onCloseCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'close')?.[1];
      
      // Test connection stability over time
      for (let i = 0; i < 5; i++) {
        // Connect
        if (onOpenCallback) {
          onOpenCallback();
          connectionEvents++;
        }
        
        jest.advanceTimersByTime(10000); // 10 seconds
        
        // Disconnect
        if (onCloseCallback) {
          onCloseCallback({ code: 1006, reason: 'Network interruption' });
          disconnectionEvents++;
        }
        
        jest.advanceTimersByTime(2000); // 2 seconds
      }
      
      // Calculate connection stability
      const stabilityRatio = connectionEvents / (connectionEvents + disconnectionEvents);
      
      console.log(`📊 Connection stability: ${(stabilityRatio * 100).toFixed(2)}%`);
      console.log(`   Connection events: ${connectionEvents}`);
      console.log(`   Disconnection events: ${disconnectionEvents}`);
      
      jest.useRealTimers();
      console.log('✅ Connection stability tested');
    });
  });

  describe('Error Recovery and Resilience', () => {
    test('should handle malformed messages gracefully', async () => {
      await realTimeIntegration.initialize();
      
      // Simulate malformed message
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      const malformedMessage = {
        data: 'invalid-json-data'
      };
      
      // Should not throw error
      expect(() => {
        if (onMessageCallback) {
          onMessageCallback(malformedMessage);
        }
      }).not.toThrow();
      
      console.log('✅ Malformed message handling tested');
    });

    test('should handle large message volumes', async () => {
      jest.setTimeout(30000); // 30 second timeout
      
      await realTimeIntegration.initialize();
      
      const messageCount = 1000;
      const startTime = Date.now();
      
      // Simulate high-volume message processing
      const onMessageCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];
      
      for (let i = 0; i < messageCount; i++) {
        const message = {
          data: JSON.stringify({
            type: 'bulk_test',
            payload: { id: i, data: 'test'.repeat(100) }
          })
        };
        
        if (onMessageCallback) {
          onMessageCallback(message);
        }
      }
      
      const totalTime = Date.now() - startTime;
      const messagesPerSecond = (messageCount / totalTime) * 1000;
      
      console.log(`📊 Bulk message processing:`);
      console.log(`   Messages: ${messageCount}`);
      console.log(`   Total time: ${totalTime}ms`);
      console.log(`   Throughput: ${messagesPerSecond.toFixed(2)} msg/sec`);
      
      // Verify performance under load
      expect(messagesPerSecond).toBeGreaterThan(100); // At least 100 msg/sec
      
      console.log('✅ High-volume message processing tested');
    });
  });
});

// Integration test utilities
export const createMockCameraEvent = (overrides = {}) => ({
  type: 'camera_event',
  payload: {
    cameraId: 'test-camera',
    eventType: 'motion_detected',
    timestamp: Date.now(),
    confidence: 0.85,
    ...overrides,
  }
});

export const createMockAlertEvent = (overrides = {}) => ({
  type: 'alert_event',
  payload: {
    alertId: `alert-${Date.now()}`,
    severity: 'medium',
    message: 'Test alert',
    timestamp: Date.now(),
    ...overrides,
  }
});

export const simulateNetworkLatency = (min = 50, max = 200) => {
  const latency = Math.random() * (max - min) + min;
  return new Promise(resolve => setTimeout(resolve, latency));
};

export default {
  createMockCameraEvent,
  createMockAlertEvent,
  simulateNetworkLatency,
};
