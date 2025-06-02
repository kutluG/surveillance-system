import React, { useEffect, useContext } from 'react';
import { Platform, Alert, Linking } from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import messaging from '@react-native-firebase/messaging';
import notifee, { TriggerType, RepeatFrequency } from '@notifee/react-native';
import { AuthContext } from '../contexts/AuthContext';
import { addAlert } from '../store/slices/alertsSlice';
import { 
  selectPushNotificationsEnabled, 
  selectAlertSoundEnabled,
  selectVibrationEnabled,
  setPushNotificationsEnabled 
} from '../store/slices/appSlice';
import { alertService } from '../services/alertService';
import { COLORS } from '../constants';

const NotificationManager = () => {
  const dispatch = useDispatch();
  const { user } = useContext(AuthContext);
  const pushNotificationsEnabled = useSelector(selectPushNotificationsEnabled);
  const alertSoundEnabled = useSelector(selectAlertSoundEnabled);
  const vibrationEnabled = useSelector(selectVibrationEnabled);

  useEffect(() => {
    if (user && pushNotificationsEnabled) {
      initializeNotifications();
    }
  }, [user, pushNotificationsEnabled]);

  const initializeNotifications = async () => {
    try {
      // Request permission
      const permission = await requestNotificationPermission();
      if (!permission) {
        dispatch(setPushNotificationsEnabled(false));
        return;
      }

      // Setup notification channel for Android
      if (Platform.OS === 'android') {
        await createNotificationChannels();
      }

      // Get FCM token and register device
      const token = await messaging().getToken();
      await registerDeviceToken(token);

      // Setup message handlers
      setupMessageHandlers();

      console.log('Notifications initialized successfully');
    } catch (error) {
      console.error('Failed to initialize notifications:', error);
    }
  };

  const requestNotificationPermission = async () => {
    try {
      if (Platform.OS === 'android') {
        const settings = await notifee.requestPermission();
        return settings.authorizationStatus === 1; // AUTHORIZED
      } else {
        const authStatus = await messaging().requestPermission();
        return (
          authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
          authStatus === messaging.AuthorizationStatus.PROVISIONAL
        );
      }
    } catch (error) {
      console.error('Permission request failed:', error);
      return false;
    }
  };

  const createNotificationChannels = async () => {
    try {
      // Critical alerts channel
      await notifee.createChannel({
        id: 'critical-alerts',
        name: 'Critical Alerts',
        importance: 5, // HIGH
        sound: alertSoundEnabled ? 'default' : undefined,
        vibration: vibrationEnabled,
        lights: true,
        lightColor: COLORS.error,
        badge: true,
      });

      // General alerts channel
      await notifee.createChannel({
        id: 'general-alerts',
        name: 'General Alerts',
        importance: 4, // DEFAULT
        sound: alertSoundEnabled ? 'default' : undefined,
        vibration: vibrationEnabled,
        badge: true,
      });

      // System notifications channel
      await notifee.createChannel({
        id: 'system-notifications',
        name: 'System Notifications',
        importance: 3, // LOW
        badge: false,
      });

      console.log('Notification channels created');
    } catch (error) {
      console.error('Failed to create notification channels:', error);
    }
  };

  const registerDeviceToken = async (token) => {
    try {
      await alertService.registerDevice(token, Platform.OS);
      console.log('Device registered for push notifications');
    } catch (error) {
      console.error('Failed to register device:', error);
    }
  };

  const setupMessageHandlers = () => {
    // Foreground messages
    const unsubscribeForeground = messaging().onMessage(async (remoteMessage) => {
      console.log('Foreground message received:', remoteMessage);
      await handleForegroundMessage(remoteMessage);
    });

    // Background/quit state messages
    messaging().onNotificationOpenedApp((remoteMessage) => {
      console.log('Notification opened app:', remoteMessage);
      handleNotificationPress(remoteMessage);
    });

    // App opened from quit state
    messaging()
      .getInitialNotification()
      .then((remoteMessage) => {
        if (remoteMessage) {
          console.log('App opened from quit state:', remoteMessage);
          handleNotificationPress(remoteMessage);
        }
      });

    // Notifee foreground event handler
    const unsubscribeNotifee = notifee.onForegroundEvent(({ type, detail }) => {
      if (type === 1) { // PRESS
        handleLocalNotificationPress(detail.notification);
      }
    });

    // Cleanup function
    return () => {
      unsubscribeForeground();
      unsubscribeNotifee();
    };
  };

  const handleForegroundMessage = async (remoteMessage) => {
    const { notification, data } = remoteMessage;
    
    // Add alert to Redux store if it's an alert notification
    if (data?.type === 'alert' && data?.alertData) {
      try {
        const alertData = JSON.parse(data.alertData);
        dispatch(addAlert(alertData));
      } catch (error) {
        console.error('Failed to parse alert data:', error);
      }
    }

    // Show local notification
    await showLocalNotification(notification, data);
  };

  const showLocalNotification = async (notification, data = {}) => {
    try {
      const channelId = getChannelId(data.severity || data.type);
      
      await notifee.displayNotification({
        title: notification?.title || 'Surveillance Alert',
        body: notification?.body || 'New activity detected',
        data: data,
        android: {
          channelId,
          smallIcon: 'ic_notification',
          color: getNotificationColor(data.severity || data.type),
          importance: getImportance(data.severity || data.type),
          autoCancel: true,
          actions: getNotificationActions(data.type),
        },
        ios: {
          sound: alertSoundEnabled ? 'default' : undefined,
          badge: true,
          critical: data.severity === 'critical',
        },
      });
    } catch (error) {
      console.error('Failed to show local notification:', error);
    }
  };

  const getChannelId = (severity) => {
    switch (severity) {
      case 'critical':
        return 'critical-alerts';
      case 'alert':
      case 'high':
      case 'medium':
        return 'general-alerts';
      default:
        return 'system-notifications';
    }
  };

  const getNotificationColor = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return COLORS.error;
      case 'medium':
        return COLORS.warning;
      case 'low':
        return COLORS.info;
      default:
        return COLORS.primary;
    }
  };

  const getImportance = (severity) => {
    switch (severity) {
      case 'critical':
        return 5; // HIGH
      case 'high':
        return 4; // DEFAULT
      case 'medium':
        return 3; // LOW
      default:
        return 2; // MIN
    }
  };

  const getNotificationActions = (type) => {
    if (type === 'alert') {
      return [
        {
          title: 'View',
          pressAction: {
            id: 'view',
          },
        },
        {
          title: 'Acknowledge',
          pressAction: {
            id: 'acknowledge',
          },
        },
      ];
    }
    return [];
  };

  const handleNotificationPress = (remoteMessage) => {
    const { data } = remoteMessage;
    
    // Navigate to appropriate screen based on notification type
    switch (data?.type) {
      case 'alert':
        // Navigate to alerts screen or specific alert
        console.log('Navigate to alerts');
        break;
      case 'camera':
        // Navigate to camera screen
        console.log('Navigate to camera');
        break;
      case 'system':
        // Navigate to settings or dashboard
        console.log('Navigate to dashboard');
        break;
      default:
        console.log('Navigate to dashboard (default)');
    }
  };

  const handleLocalNotificationPress = (notification) => {
    const { data } = notification;
    handleNotificationPress({ data });
  };

  const scheduleNotification = async (title, body, triggerTime, data = {}) => {
    try {
      const trigger = {
        type: TriggerType.TIMESTAMP,
        timestamp: triggerTime,
      };

      await notifee.createTriggerNotification(
        {
          title,
          body,
          data,
          android: {
            channelId: 'system-notifications',
            smallIcon: 'ic_notification',
          },
        },
        trigger
      );
    } catch (error) {
      console.error('Failed to schedule notification:', error);
    }
  };

  const cancelAllNotifications = async () => {
    try {
      await notifee.cancelAllNotifications();
      console.log('All notifications cancelled');
    } catch (error) {
      console.error('Failed to cancel notifications:', error);
    }
  };

  const testNotification = async () => {
    await showLocalNotification(
      {
        title: 'Test Notification',
        body: 'This is a test notification from your surveillance system.',
      },
      {
        type: 'test',
        severity: 'medium',
      }
    );
  };

  // Expose methods for external use
  React.useImperativeHandle(React.useRef(), () => ({
    showNotification: showLocalNotification,
    scheduleNotification,
    cancelAllNotifications,
    testNotification,
  }));

  return null; // This component doesn't render anything
};

export default NotificationManager;
