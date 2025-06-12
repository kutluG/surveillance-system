import { Platform } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import storage from '@react-native-firebase/storage';
import analytics from '@react-native-firebase/analytics';
import crashlytics from '@react-native-firebase/crashlytics';
import secureStorage from '../utils/secureStorage';

class FirebaseService {
  constructor() {
    this.isInitialized = false;
    this.fcmToken = null;
    this.userId = null;
  }

  async initialize() {
    try {
      console.log('Initializing Firebase services...');

      // Initialize Firebase Analytics
      await analytics().setAnalyticsCollectionEnabled(true);
      
      // Initialize Crashlytics
      await crashlytics().setCrashlyticsCollectionEnabled(true);
      
      // Request notification permissions
      await this.requestNotificationPermission();
      
      // Get FCM token
      await this.getFCMToken();
      
      // Set up message handlers
      this.setupMessageHandlers();
      
      this.isInitialized = true;
      console.log('Firebase services initialized successfully');
      
      // Track app initialization
      await this.trackEvent('app_initialized', {
        platform: Platform.OS,
        version: Platform.Version,
      });
      
    } catch (error) {
      console.error('Failed to initialize Firebase:', error);
      await this.logError(error, 'firebase_initialization_failed');
      throw error;
    }
  }

  async requestNotificationPermission() {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled = 
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        console.log('Notification permission granted');
        return true;
      } else {
        console.log('Notification permission denied');
        return false;
      }
    } catch (error) {
      console.error('Failed to request notification permission:', error);
      return false;
    }
  }
  async getFCMToken() {
    try {
      // Check if token exists in storage
      let token = await secureStorage.getItem('fcm_token');
      
      if (!token) {
        // Get new token
        token = await messaging().getToken();
        if (token) {
          await secureStorage.setItem('fcm_token', token);
        }
      }
      
      this.fcmToken = token;
      console.log('FCM Token:', token);
      
      return token;
    } catch (error) {
      console.error('Failed to get FCM token:', error);
      await this.logError(error, 'fcm_token_failed');
      return null;
    }
  }

  setupMessageHandlers() {
    // Handle foreground messages
    messaging().onMessage(async remoteMessage => {
      console.log('Foreground message received:', remoteMessage);
      await this.handleForegroundMessage(remoteMessage);
    });

    // Handle background messages
    messaging().setBackgroundMessageHandler(async remoteMessage => {
      console.log('Background message received:', remoteMessage);
      await this.handleBackgroundMessage(remoteMessage);
    });

    // Handle notification opened app
    messaging().onNotificationOpenedApp(remoteMessage => {
      console.log('Notification opened app:', remoteMessage);
      this.handleNotificationOpened(remoteMessage);
    });

    // Check if app was opened from notification
    messaging()
      .getInitialNotification()
      .then(remoteMessage => {
        if (remoteMessage) {
          console.log('App opened from notification:', remoteMessage);
          this.handleNotificationOpened(remoteMessage);
        }
      });    // Listen for token refresh
    messaging().onTokenRefresh(token => {
      console.log('FCM token refreshed:', token);
      this.fcmToken = token;
      secureStorage.setItem('fcm_token', token);
      this.updateTokenOnServer(token);
    });
  }

  async handleForegroundMessage(remoteMessage) {
    try {
      const { notification, data } = remoteMessage;
      
      // Track notification received
      await this.trackEvent('notification_received_foreground', {
        type: data?.type || 'unknown',
        title: notification?.title,
      });

      // Show local notification if needed
      if (notification) {
        // This would integrate with your NotificationManager
        // NotificationManager.showLocalNotification(notification, data);
      }

      // Handle data-only messages
      if (data) {
        await this.handleNotificationData(data);
      }
    } catch (error) {
      console.error('Failed to handle foreground message:', error);
      await this.logError(error, 'foreground_message_handling_failed');
    }
  }

  async handleBackgroundMessage(remoteMessage) {
    try {
      const { data } = remoteMessage;
      
      // Track notification received
      await this.trackEvent('notification_received_background', {
        type: data?.type || 'unknown',
      });

      // Handle critical data updates
      if (data) {
        await this.handleNotificationData(data);
      }
    } catch (error) {
      console.error('Failed to handle background message:', error);
      await this.logError(error, 'background_message_handling_failed');
    }
  }

  handleNotificationOpened(remoteMessage) {
    try {
      const { data } = remoteMessage;
      
      // Track notification opened
      this.trackEvent('notification_opened', {
        type: data?.type || 'unknown',
      });

      // Navigate based on notification type
      if (data?.type) {
        this.handleNotificationNavigation(data);
      }
    } catch (error) {
      console.error('Failed to handle notification opened:', error);
      this.logError(error, 'notification_opened_handling_failed');
    }
  }

  async handleNotificationData(data) {
    try {
      switch (data.type) {
        case 'alert':
          await this.handleAlertNotification(data);
          break;
        case 'camera_status':
          await this.handleCameraStatusNotification(data);
          break;
        case 'system_update':
          await this.handleSystemUpdateNotification(data);
          break;
        default:
          console.log('Unknown notification type:', data.type);
      }
    } catch (error) {
      console.error('Failed to handle notification data:', error);
      await this.logError(error, 'notification_data_handling_failed');
    }
  }

  async handleAlertNotification(data) {
    // Update local alert data
    // This would integrate with your Redux store
    console.log('Handling alert notification:', data);
  }

  async handleCameraStatusNotification(data) {
    // Update camera status
    console.log('Handling camera status notification:', data);
  }

  async handleSystemUpdateNotification(data) {
    // Handle system updates
    console.log('Handling system update notification:', data);
  }

  handleNotificationNavigation(data) {
    // This would integrate with your navigation system
    console.log('Handling notification navigation:', data);
  }

  async updateTokenOnServer(token) {
    try {
      if (!this.userId) {
        console.log('No user ID available for token update');
        return;
      }

      // Update token in Firestore
      await firestore()
        .collection('users')
        .doc(this.userId)
        .update({
          fcmToken: token,
          tokenUpdatedAt: firestore.FieldValue.serverTimestamp(),
        });

      console.log('FCM token updated on server');
    } catch (error) {
      console.error('Failed to update token on server:', error);
      await this.logError(error, 'token_server_update_failed');
    }
  }

  async authenticateUser(email, password) {
    try {
      const userCredential = await auth().signInWithEmailAndPassword(email, password);
      this.userId = userCredential.user.uid;
      
      // Update FCM token for this user
      if (this.fcmToken) {
        await this.updateTokenOnServer(this.fcmToken);
      }

      await this.trackEvent('user_login', {
        method: 'email_password',
      });

      return userCredential.user;
    } catch (error) {
      console.error('Authentication failed:', error);
      await this.logError(error, 'authentication_failed');
      throw error;
    }
  }

  async signOut() {
    try {
      await auth().signOut();
      this.userId = null;
      
      await this.trackEvent('user_logout');
      
      console.log('User signed out successfully');
    } catch (error) {
      console.error('Sign out failed:', error);
      await this.logError(error, 'signout_failed');
      throw error;
    }
  }

  async uploadFile(filePath, fileName, folder = 'uploads') {
    try {
      const reference = storage().ref(`${folder}/${fileName}`);
      const task = reference.putFile(filePath);

      // Monitor upload progress
      task.on('state_changed', taskSnapshot => {
        const progress = (taskSnapshot.bytesTransferred / taskSnapshot.totalBytes) * 100;
        console.log(`Upload progress: ${progress}%`);
      });

      await task;
      const downloadURL = await reference.getDownloadURL();
      
      await this.trackEvent('file_uploaded', {
        folder,
        fileSize: (await reference.getMetadata()).size,
      });

      return downloadURL;
    } catch (error) {
      console.error('File upload failed:', error);
      await this.logError(error, 'file_upload_failed');
      throw error;
    }
  }

  async saveDocument(collection, docId, data) {
    try {
      await firestore()
        .collection(collection)
        .doc(docId)
        .set(data, { merge: true });

      await this.trackEvent('document_saved', {
        collection,
      });

      console.log('Document saved successfully');
    } catch (error) {
      console.error('Failed to save document:', error);
      await this.logError(error, 'document_save_failed');
      throw error;
    }
  }

  async getDocument(collection, docId) {
    try {
      const doc = await firestore()
        .collection(collection)
        .doc(docId)
        .get();

      if (doc.exists) {
        return doc.data();
      } else {
        return null;
      }
    } catch (error) {
      console.error('Failed to get document:', error);
      await this.logError(error, 'document_get_failed');
      throw error;
    }
  }

  async trackEvent(eventName, parameters = {}) {
    try {
      await analytics().logEvent(eventName, parameters);
    } catch (error) {
      console.error('Failed to track event:', error);
    }
  }

  async logError(error, context = '') {
    try {
      await crashlytics().recordError(error);
      
      if (context) {
        await crashlytics().log(`Context: ${context}`);
      }
    } catch (crashError) {
      console.error('Failed to log error to Crashlytics:', crashError);
    }
  }

  async setUserProperties(properties) {
    try {
      for (const [key, value] of Object.entries(properties)) {
        await analytics().setUserProperty(key, String(value));
      }
    } catch (error) {
      console.error('Failed to set user properties:', error);
    }
  }

  getFCMTokenSync() {
    return this.fcmToken;
  }

  getUserId() {
    return this.userId;
  }

  isServiceInitialized() {
    return this.isInitialized;
  }
}

export default new FirebaseService();
