import { store } from '../store';
import { setCameras, updateCameraStatus, updateCameraStats } from '../store/slices/camerasSlice';
import { addAlert, updateAlert, markAlertAsRead } from '../store/slices/alertsSlice';
import { updateDashboardStats, setSystemStatus } from '../store/slices/appSlice';
import websocketService from './websocketService';

class RealTimeIntegration {
  constructor() {
    this.isInitialized = false;
    this.subscriptions = new Map();
  }

  initialize() {
    if (this.isInitialized) {
      return;
    }

    this.setupWebSocketHandlers();
    this.isInitialized = true;
  }

  setupWebSocketHandlers() {
    // Camera-related real-time updates
    websocketService.subscribe('camera/status', this.handleCameraStatusUpdate.bind(this));
    websocketService.subscribe('camera/stats', this.handleCameraStatsUpdate.bind(this));
    websocketService.subscribe('camera/list', this.handleCameraListUpdate.bind(this));
    websocketService.subscribe('camera/stream', this.handleCameraStreamUpdate.bind(this));

    // Alert-related real-time updates
    websocketService.subscribe('alert/new', this.handleNewAlert.bind(this));
    websocketService.subscribe('alert/update', this.handleAlertUpdate.bind(this));
    websocketService.subscribe('alert/acknowledged', this.handleAlertAcknowledged.bind(this));

    // System-wide updates
    websocketService.subscribe('system/stats', this.handleSystemStatsUpdate.bind(this));
    websocketService.subscribe('system/status', this.handleSystemStatusUpdate.bind(this));
    websocketService.subscribe('system/health', this.handleSystemHealthUpdate.bind(this));

    // Video and recording updates
    websocketService.subscribe('recording/new', this.handleNewRecording.bind(this));
    websocketService.subscribe('recording/status', this.handleRecordingStatusUpdate.bind(this));
  }

  handleCameraStatusUpdate(data) {
    try {
      const { cameraId, status, timestamp } = data;
      store.dispatch(updateCameraStatus({
        id: cameraId,
        status,
        lastSeen: timestamp
      }));
    } catch (error) {
      console.error('Error handling camera status update:', error);
    }
  }

  handleCameraStatsUpdate(data) {
    try {
      const { cameraId, stats } = data;
      store.dispatch(updateCameraStats({
        id: cameraId,
        stats
      }));
    } catch (error) {
      console.error('Error handling camera stats update:', error);
    }
  }

  handleCameraListUpdate(data) {
    try {
      const { cameras } = data;
      store.dispatch(setCameras(cameras));
    } catch (error) {
      console.error('Error handling camera list update:', error);
    }
  }

  handleCameraStreamUpdate(data) {
    try {
      const { cameraId, streamUrl, quality, frameRate } = data;
      store.dispatch(updateCameraStatus({
        id: cameraId,
        streamUrl,
        quality,
        frameRate,
        lastUpdated: new Date().toISOString()
      }));
    } catch (error) {
      console.error('Error handling camera stream update:', error);
    }
  }

  handleNewAlert(data) {
    try {
      store.dispatch(addAlert(data));
      
      // Show local notification for new alerts
      this.showLocalNotification({
        title: 'New Security Alert',
        body: `${data.type} detected at ${data.cameraName}`,
        data: { alertId: data.id, type: 'alert' }
      });
    } catch (error) {
      console.error('Error handling new alert:', error);
    }
  }

  handleAlertUpdate(data) {
    try {
      const { alertId, updates } = data;
      store.dispatch(updateAlert({
        id: alertId,
        updates
      }));
    } catch (error) {
      console.error('Error handling alert update:', error);
    }
  }

  handleAlertAcknowledged(data) {
    try {
      const { alertId, acknowledgedBy, timestamp } = data;
      store.dispatch(markAlertAsRead({
        alertId,
        acknowledgedBy,
        acknowledgedAt: timestamp
      }));
    } catch (error) {
      console.error('Error handling alert acknowledgment:', error);
    }
  }

  handleSystemStatsUpdate(data) {
    try {
      store.dispatch(updateDashboardStats(data));
    } catch (error) {
      console.error('Error handling system stats update:', error);
    }
  }

  handleSystemStatusUpdate(data) {
    try {
      store.dispatch(setSystemStatus(data));
    } catch (error) {
      console.error('Error handling system status update:', error);
    }
  }

  handleSystemHealthUpdate(data) {
    try {
      const { services, timestamp } = data;
      store.dispatch(setSystemStatus({
        health: services,
        lastHealthCheck: timestamp
      }));
    } catch (error) {
      console.error('Error handling system health update:', error);
    }
  }

  handleNewRecording(data) {
    try {
      // Update recordings in the appropriate slice if we have one
      // For now, we'll just log it
      console.log('New recording available:', data);
    } catch (error) {
      console.error('Error handling new recording:', error);
    }
  }

  handleRecordingStatusUpdate(data) {
    try {
      const { recordingId, status, duration, size } = data;
      console.log('Recording status update:', { recordingId, status, duration, size });
    } catch (error) {
      console.error('Error handling recording status update:', error);
    }
  }

  showLocalNotification(notification) {
    // This will be implemented with the notification service
    console.log('Local notification:', notification);
  }

  // Method to start real-time monitoring for specific cameras
  startCameraMonitoring(cameraIds) {
    try {
      cameraIds.forEach(cameraId => {
        websocketService.send('camera/monitor/start', { cameraId });
      });
    } catch (error) {
      console.error('Error starting camera monitoring:', error);
    }
  }

  // Method to stop real-time monitoring for specific cameras
  stopCameraMonitoring(cameraIds) {
    try {
      cameraIds.forEach(cameraId => {
        websocketService.send('camera/monitor/stop', { cameraId });
      });
    } catch (error) {
      console.error('Error stopping camera monitoring:', error);
    }
  }

  // Method to request live stream for a camera
  requestLiveStream(cameraId, quality = 'medium') {
    try {
      websocketService.send('camera/stream/request', { 
        cameraId, 
        quality,
        mobile: true 
      });
    } catch (error) {
      console.error('Error requesting live stream:', error);
    }
  }

  // Method to acknowledge an alert via WebSocket
  acknowledgeAlert(alertId) {
    try {
      websocketService.send('alert/acknowledge', { 
        alertId,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  }

  // Method to request system statistics
  requestSystemStats() {
    try {
      websocketService.send('system/stats/request', {
        includeDetailed: true
      });
    } catch (error) {
      console.error('Error requesting system stats:', error);
    }
  }

  cleanup() {
    try {
      this.subscriptions.clear();
      this.isInitialized = false;
    } catch (error) {
      console.error('Error during real-time integration cleanup:', error);
    }
  }
}

export default new RealTimeIntegration();
