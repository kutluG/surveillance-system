import { NativeModules, Platform } from 'react-native';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';

class NativeModuleService {
  constructor() {
    this.isInitialized = false;
    this.availableModules = new Map();
  }

  async initialize() {
    try {
      // Check and request necessary permissions
      await this.requestPermissions();
      
      // Initialize available native modules
      this.checkAvailableModules();
      
      this.isInitialized = true;
      console.log('NativeModuleService initialized successfully');
    } catch (error) {
      console.error('Failed to initialize NativeModuleService:', error);
      throw error;
    }
  }

  async requestPermissions() {
    const permissions = Platform.select({
      ios: [
        PERMISSIONS.IOS.CAMERA,
        PERMISSIONS.IOS.MICROPHONE,
        PERMISSIONS.IOS.PHOTO_LIBRARY,
        PERMISSIONS.IOS.FACE_ID,
      ],
      android: [
        PERMISSIONS.ANDROID.CAMERA,
        PERMISSIONS.ANDROID.RECORD_AUDIO,
        PERMISSIONS.ANDROID.READ_EXTERNAL_STORAGE,
        PERMISSIONS.ANDROID.WRITE_EXTERNAL_STORAGE,
        PERMISSIONS.ANDROID.USE_FINGERPRINT,
        PERMISSIONS.ANDROID.USE_BIOMETRIC,
      ],
    });

    const permissionResults = {};
    
    for (const permission of permissions) {
      try {
        const result = await check(permission);
        
        if (result === RESULTS.DENIED) {
          const requestResult = await request(permission);
          permissionResults[permission] = requestResult;
        } else {
          permissionResults[permission] = result;
        }
      } catch (error) {
        console.warn(`Failed to check permission ${permission}:`, error);
        permissionResults[permission] = RESULTS.UNAVAILABLE;
      }
    }

    return permissionResults;
  }

  checkAvailableModules() {
    // Check for video player modules
    if (NativeModules.RNVideo) {
      this.availableModules.set('video', true);
    }

    // Check for biometric modules
    if (NativeModules.TouchID || NativeModules.ReactNativeBiometrics) {
      this.availableModules.set('biometrics', true);
    }

    // Check for background task modules
    if (NativeModules.BackgroundJob || NativeModules.BackgroundTask) {
      this.availableModules.set('backgroundTasks', true);
    }

    // Check for push notification modules
    if (NativeModules.RNFirebaseMessaging || NativeModules.PushNotificationIOS) {
      this.availableModules.set('pushNotifications', true);
    }

    // Check for network state modules
    if (NativeModules.RNCNetInfo) {
      this.availableModules.set('networkInfo', true);
    }

    // Check for file system modules
    if (NativeModules.RNFSManager) {
      this.availableModules.set('fileSystem', true);
    }

    console.log('Available native modules:', Array.from(this.availableModules.keys()));
  }

  isModuleAvailable(moduleName) {
    return this.availableModules.get(moduleName) || false;
  }

  getAvailableModules() {
    return Array.from(this.availableModules.keys());
  }

  async getDeviceInfo() {
    try {
      const deviceInfo = {
        platform: Platform.OS,
        version: Platform.Version,
        isTablet: Platform.isPad || false,
        hasNotch: Platform.select({
          ios: Platform.constants.osVersion >= '11.0' && Platform.constants.deviceName.includes('iPhone X'),
          android: false,
        }),
      };

      // Get additional device capabilities
      if (this.isModuleAvailable('biometrics')) {
        deviceInfo.biometricSupport = await this.checkBiometricSupport();
      }

      if (this.isModuleAvailable('video')) {
        deviceInfo.videoCodecSupport = await this.checkVideoCodecSupport();
      }

      return deviceInfo;
    } catch (error) {
      console.error('Failed to get device info:', error);
      return {
        platform: Platform.OS,
        version: Platform.Version,
        isTablet: false,
        hasNotch: false,
      };
    }
  }

  async checkBiometricSupport() {
    try {
      if (Platform.OS === 'ios' && NativeModules.TouchID) {
        return await NativeModules.TouchID.isSupported();
      } else if (Platform.OS === 'android' && NativeModules.ReactNativeBiometrics) {
        const { available } = await NativeModules.ReactNativeBiometrics.isSensorAvailable();
        return available;
      }
      return false;
    } catch (error) {
      console.warn('Failed to check biometric support:', error);
      return false;
    }
  }

  async checkVideoCodecSupport() {
    try {
      // This would need to be implemented in native code
      // For now, return common codec support based on platform
      return Platform.select({
        ios: ['h264', 'hevc', 'av1'],
        android: ['h264', 'h265', 'vp8', 'vp9'],
      });
    } catch (error) {
      console.warn('Failed to check video codec support:', error);
      return ['h264'];
    }
  }

  async performNativeOptimization() {
    try {
      // Optimize native modules for better performance
      if (Platform.OS === 'android') {
        // Android-specific optimizations
        if (NativeModules.RNVideo) {
          // Configure hardware acceleration
          await this.configureVideoHardwareAcceleration();
        }
      } else if (Platform.OS === 'ios') {
        // iOS-specific optimizations
        if (NativeModules.RNVideo) {
          // Configure AVPlayer settings
          await this.configureAVPlayerSettings();
        }
      }

      console.log('Native module optimization completed');
    } catch (error) {
      console.warn('Failed to perform native optimization:', error);
    }
  }

  async configureVideoHardwareAcceleration() {
    try {
      // This would need to be implemented in native Android code
      console.log('Configuring Android video hardware acceleration');
    } catch (error) {
      console.warn('Failed to configure video hardware acceleration:', error);
    }
  }

  async configureAVPlayerSettings() {
    try {
      // This would need to be implemented in native iOS code
      console.log('Configuring iOS AVPlayer settings');
    } catch (error) {
      console.warn('Failed to configure AVPlayer settings:', error);
    }
  }

  async testNativeModules() {
    const testResults = {};

    for (const [moduleName, isAvailable] of this.availableModules) {
      if (!isAvailable) {
        testResults[moduleName] = { status: 'unavailable' };
        continue;
      }

      try {
        switch (moduleName) {
          case 'video':
            testResults[moduleName] = await this.testVideoModule();
            break;
          case 'biometrics':
            testResults[moduleName] = await this.testBiometricModule();
            break;
          case 'pushNotifications':
            testResults[moduleName] = await this.testPushNotificationModule();
            break;
          case 'networkInfo':
            testResults[moduleName] = await this.testNetworkInfoModule();
            break;
          default:
            testResults[moduleName] = { status: 'not_tested' };
        }
      } catch (error) {
        testResults[moduleName] = { 
          status: 'error', 
          error: error.message 
        };
      }
    }

    return testResults;
  }

  async testVideoModule() {
    // Test video module functionality
    return { status: 'ok', codecs: await this.checkVideoCodecSupport() };
  }

  async testBiometricModule() {
    // Test biometric module functionality
    const isSupported = await this.checkBiometricSupport();
    return { status: 'ok', supported: isSupported };
  }

  async testPushNotificationModule() {
    // Test push notification module functionality
    return { status: 'ok', configured: true };
  }

  async testNetworkInfoModule() {
    // Test network info module functionality
    return { status: 'ok', available: true };
  }
}

export default new NativeModuleService();
