import ReactNativeBiometrics from 'react-native-biometrics';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';

class BiometricService {
  constructor() {
    this.rnBiometrics = new ReactNativeBiometrics({
      allowDeviceCredentials: true
    });
  }

  async checkBiometricAvailability() {
    try {
      const { available, biometryType } = await this.rnBiometrics.isSensorAvailable();
      return {
        available,
        biometryType,
        isSupported: available && (biometryType === ReactNativeBiometrics.TouchID || 
                                   biometryType === ReactNativeBiometrics.FaceID ||
                                   biometryType === ReactNativeBiometrics.Biometrics)
      };
    } catch (error) {
      console.error('Error checking biometric availability:', error);
      return { available: false, isSupported: false };
    }
  }

  async isBiometricEnabled() {
    try {
      const enabled = await AsyncStorage.getItem('biometric_enabled');
      return enabled === 'true';
    } catch (error) {
      console.error('Error checking biometric setting:', error);
      return false;
    }
  }

  async setBiometricEnabled(enabled) {
    try {
      await AsyncStorage.setItem('biometric_enabled', enabled.toString());
      return true;
    } catch (error) {
      console.error('Error setting biometric preference:', error);
      return false;
    }
  }

  async authenticateWithBiometric(promptMessage = 'Please authenticate to access the app') {
    try {
      const biometricEnabled = await this.isBiometricEnabled();
      if (!biometricEnabled) {
        return { success: false, error: 'Biometric authentication is disabled' };
      }

      const { available } = await this.checkBiometricAvailability();
      if (!available) {
        return { success: false, error: 'Biometric authentication is not available' };
      }

      const { success, error } = await this.rnBiometrics.simplePrompt({
        promptMessage,
        cancelButtonText: 'Cancel'
      });

      return { success, error };
    } catch (error) {
      console.error('Biometric authentication error:', error);
      return { success: false, error: error.message };
    }
  }

  async setupBiometricAuthentication() {
    try {
      const { available, biometryType } = await this.checkBiometricAvailability();
      
      if (!available) {
        Alert.alert(
          'Biometric Not Available',
          'Biometric authentication is not available on this device.',
          [{ text: 'OK' }]
        );
        return false;
      }

      const biometricTypeText = this.getBiometricTypeText(biometryType);
      
      return new Promise((resolve) => {
        Alert.alert(
          'Enable Biometric Authentication',
          `Would you like to enable ${biometricTypeText} for quick and secure login?`,
          [
            {
              text: 'Cancel',
              style: 'cancel',
              onPress: () => resolve(false)
            },
            {
              text: 'Enable',
              onPress: async () => {
                const authResult = await this.authenticateWithBiometric(
                  `Please authenticate with ${biometricTypeText} to enable this feature`
                );
                
                if (authResult.success) {
                  await this.setBiometricEnabled(true);
                  resolve(true);
                } else {
                  Alert.alert('Authentication Failed', authResult.error);
                  resolve(false);
                }
              }
            }
          ]
        );
      });
    } catch (error) {
      console.error('Error setting up biometric authentication:', error);
      return false;
    }
  }

  getBiometricTypeText(biometryType) {
    switch (biometryType) {
      case ReactNativeBiometrics.TouchID:
        return 'Touch ID';
      case ReactNativeBiometrics.FaceID:
        return 'Face ID';
      case ReactNativeBiometrics.Biometrics:
        return 'Fingerprint';
      default:
        return 'Biometric Authentication';
    }
  }

  async disableBiometricAuthentication() {
    try {
      await this.setBiometricEnabled(false);
      return true;
    } catch (error) {
      console.error('Error disabling biometric authentication:', error);
      return false;
    }
  }

  async promptForBiometricSetup() {
    const { available } = await this.checkBiometricAvailability();
    const enabled = await this.isBiometricEnabled();
    
    if (available && !enabled) {
      setTimeout(() => {
        this.setupBiometricAuthentication();
      }, 1000); // Delay to allow UI to settle
    }
  }
}

export default new BiometricService();
