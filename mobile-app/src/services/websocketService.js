import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG } from '../constants';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 5000;
    this.listeners = new Map();
    this.isConnecting = false;
    this.connectionStatus = 'disconnected';
  }

  async connect() {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.isConnecting = true;
      const token = await AsyncStorage.getItem('token');
      
      if (!token) {
        throw new Error('No authentication token available');
      }

      const wsUrl = `${API_CONFIG.WEBSOCKET_URL}?token=${token}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.connectionStatus = 'connected';
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.notifyListeners('connection', { status: 'connected' });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.connectionStatus = 'disconnected';
        this.isConnecting = false;
        this.notifyListeners('connection', { status: 'disconnected' });
        
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatus = 'error';
        this.isConnecting = false;
        this.notifyListeners('connection', { status: 'error', error });
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.isConnecting = false;
      this.connectionStatus = 'error';
      this.notifyListeners('connection', { status: 'error', error });
    }
  }

  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    this.connectionStatus = 'disconnected';
    this.reconnectAttempts = 0;
  }

  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket not connected, cannot send message');
    return false;
  }

  subscribe(topic, callback) {
    if (!this.listeners.has(topic)) {
      this.listeners.set(topic, new Set());
    }
    this.listeners.get(topic).add(callback);

    // Send subscription message if connected
    this.send({
      type: 'subscribe',
      topic
    });

    // Return unsubscribe function
    return () => {
      const topicListeners = this.listeners.get(topic);
      if (topicListeners) {
        topicListeners.delete(callback);
        if (topicListeners.size === 0) {
          this.listeners.delete(topic);
          this.send({
            type: 'unsubscribe',
            topic
          });
        }
      }
    };
  }

  unsubscribe(topic, callback) {
    const topicListeners = this.listeners.get(topic);
    if (topicListeners) {
      topicListeners.delete(callback);
      if (topicListeners.size === 0) {
        this.listeners.delete(topic);
        this.send({
          type: 'unsubscribe',
          topic
        });
      }
    }
  }

  handleMessage(data) {
    const { type, topic, payload } = data;

    // Handle specific message types
    switch (type) {
      case 'camera_feed':
        this.notifyListeners('camera_feeds', payload);
        break;
      case 'alert':
        this.notifyListeners('alerts', payload);
        break;
      case 'detection':
        this.notifyListeners('detections', payload);
        break;
      case 'system_status':
        this.notifyListeners('system_status', payload);
        break;
      case 'notification':
        this.notifyListeners('notifications', payload);
        break;
      default:
        // Handle topic-based messages
        if (topic) {
          this.notifyListeners(topic, payload);
        }
        break;
    }
  }

  notifyListeners(topic, data) {
    const topicListeners = this.listeners.get(topic);
    if (topicListeners) {
      topicListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket listener for topic ${topic}:`, error);
        }
      });
    }
  }

  getConnectionStatus() {
    return this.connectionStatus;
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // Camera specific methods
  subscribeCameraFeed(cameraId, callback) {
    return this.subscribe(`camera_${cameraId}`, callback);
  }

  unsubscribeCameraFeed(cameraId, callback) {
    this.unsubscribe(`camera_${cameraId}`, callback);
  }

  requestCameraFeed(cameraId) {
    this.send({
      type: 'request_camera_feed',
      camera_id: cameraId
    });
  }

  // Alert specific methods
  subscribeAlerts(callback) {
    return this.subscribe('alerts', callback);
  }

  acknowledgeAlert(alertId) {
    this.send({
      type: 'acknowledge_alert',
      alert_id: alertId
    });
  }

  // System monitoring methods
  subscribeSystemStatus(callback) {
    return this.subscribe('system_status', callback);
  }

  requestSystemStatus() {
    this.send({
      type: 'request_system_status'
    });
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
