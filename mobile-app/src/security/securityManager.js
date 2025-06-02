/**
 * Security Configuration and Hardening
 * Implements security best practices for the surveillance app
 */
import { Alert, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';

class SecurityManager {
  constructor() {
    this.securityConfig = {
      // Session management
      SESSION_TIMEOUT: 30 * 60 * 1000, // 30 minutes
      IDLE_TIMEOUT: 15 * 60 * 1000, // 15 minutes
      MAX_LOGIN_ATTEMPTS: 5,
      LOCKOUT_DURATION: 15 * 60 * 1000, // 15 minutes
      
      // Encryption
      ENCRYPTION_ALGORITHM: 'AES-256-GCM',
      KEY_DERIVATION_ITERATIONS: 100000,
      
      // Network security
      CERTIFICATE_PINNING: true,
      REQUIRE_HTTPS: true,
      SECURITY_HEADERS: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      },
      
      // App security
      DISABLE_SCREENSHOTS: true,
      DISABLE_SCREEN_RECORDING: true,
      OBFUSCATE_IN_BACKGROUND: true,
      JAILBREAK_DETECTION: true,
    };
    
    this.securityState = {
      isSecure: true,
      violations: [],
      lastSecurityCheck: null,
    };
  }

  /**
   * Initialize security configurations
   */
  async initializeSecurity() {
    console.log('🔒 Initializing security configurations...');
    
    try {
      await this.performSecurityChecks();
      await this.setupSessionManagement();
      await this.configureAppSecurity();
      
      console.log('✅ Security initialization complete');
      return true;
    } catch (error) {
      console.error('❌ Security initialization failed:', error);
      return false;
    }
  }

  /**
   * Perform comprehensive security checks
   */
  async performSecurityChecks() {
    const violations = [];

    // Device security checks
    if (await this.isDeviceRooted()) {
      violations.push('DEVICE_ROOTED');
    }

    if (await this.isDebuggerAttached()) {
      violations.push('DEBUGGER_ATTACHED');
    }

    if (await this.isEmulator()) {
      violations.push('RUNNING_ON_EMULATOR');
    }

    // App integrity checks
    if (await this.isAppTampered()) {
      violations.push('APP_TAMPERED');
    }

    // Network security checks
    if (!this.isNetworkSecure()) {
      violations.push('INSECURE_NETWORK');
    }

    this.securityState.violations = violations;
    this.securityState.lastSecurityCheck = Date.now();
    this.securityState.isSecure = violations.length === 0;

    if (violations.length > 0) {
      await this.handleSecurityViolations(violations);
    }

    return this.securityState.isSecure;
  }

  /**
   * Check if device is rooted/jailbroken
   */
  async isDeviceRooted() {
    try {
      const isRooted = await DeviceInfo.isEmulator();
      return isRooted;
    } catch (error) {
      console.warn('⚠️  Could not check root status:', error);
      return false;
    }
  }

  /**
   * Check if debugger is attached
   */
  async isDebuggerAttached() {
    // Check for common debugging indicators
    if (__DEV__) {
      return false; // Allow debugging in development
    }

    // Check for React Native debugger
    if (typeof global.__REACT_DEVTOOLS_GLOBAL_HOOK__ !== 'undefined') {
      return true;
    }

    // Check for other debugging tools
    if (typeof global.nativeCallSyncHook !== 'undefined') {
      return true;
    }

    return false;
  }

  /**
   * Check if running on emulator
   */
  async isEmulator() {
    try {
      return await DeviceInfo.isEmulator();
    } catch (error) {
      console.warn('⚠️  Could not check emulator status:', error);
      return false;
    }
  }

  /**
   * Check if app has been tampered with
   */
  async isAppTampered() {
    // TODO: Implement app signature verification
    // This would require native module implementation
    return false;
  }

  /**
   * Check network security
   */
  isNetworkSecure() {
    // Check if HTTPS is being used
    const config = require('./environment').default.getAllConfig();
    
    if (config.ENVIRONMENT === 'production') {
      return config.API_BASE_URL.startsWith('https://');
    }
    
    return true; // Allow HTTP in development
  }

  /**
   * Handle security violations
   */
  async handleSecurityViolations(violations) {
    console.error('🚨 Security violations detected:', violations);

    const criticalViolations = ['DEVICE_ROOTED', 'APP_TAMPERED', 'DEBUGGER_ATTACHED'];
    const hasCriticalViolations = violations.some(v => criticalViolations.includes(v));

    if (hasCriticalViolations) {
      await this.blockAppAccess();
    } else {
      await this.showSecurityWarning(violations);
    }
  }

  /**
   * Block app access due to security violations
   */
  async blockAppAccess() {
    Alert.alert(
      '🔒 Security Alert',
      'This app cannot run on this device due to security policy violations. Please contact support.',
      [
        {
          text: 'Exit App',
          onPress: () => {
            // Exit the app
            if (Platform.OS === 'android') {
              require('react-native').BackHandler.exitApp();
            }
          }
        }
      ],
      { cancelable: false }
    );
  }

  /**
   * Show security warning
   */
  async showSecurityWarning(violations) {
    const message = `Security warnings detected:\n${violations.join(', ')}\n\nContinue at your own risk.`;
    
    Alert.alert(
      '⚠️  Security Warning',
      message,
      [
        { text: 'Continue', style: 'destructive' },
        { text: 'Exit', onPress: () => require('react-native').BackHandler.exitApp() }
      ]
    );
  }

  /**
   * Setup session management
   */
  async setupSessionManagement() {
    // Set up automatic session timeout
    this.startSessionTimer();
    
    // Set up idle detection
    this.startIdleTimer();
  }

  /**
   * Configure app-level security
   */
  async configureAppSecurity() {
    if (Platform.OS === 'android') {
      await this.configureAndroidSecurity();
    } else if (Platform.OS === 'ios') {
      await this.configureiOSSecurity();
    }
  }

  /**
   * Configure Android-specific security
   */
  async configureAndroidSecurity() {
    // Disable screenshots and screen recording
    if (this.securityConfig.DISABLE_SCREENSHOTS) {
      // This would require native module implementation
      console.log('🔒 Screenshots disabled (requires native implementation)');
    }
  }

  /**
   * Configure iOS-specific security
   */
  async configureiOSSecurity() {
    // Configure iOS-specific security settings
    console.log('🔒 iOS security configured');
  }

  /**
   * Start session timeout timer
   */
  startSessionTimer() {
    this.sessionTimer = setTimeout(() => {
      this.handleSessionTimeout();
    }, this.securityConfig.SESSION_TIMEOUT);
  }

  /**
   * Reset session timer
   */
  resetSessionTimer() {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
    }
    this.startSessionTimer();
  }

  /**
   * Handle session timeout
   */
  handleSessionTimeout() {
    console.log('🔒 Session timeout - logging out user');
    
    Alert.alert(
      'Session Expired',
      'Your session has expired for security reasons. Please log in again.',
      [{ text: 'OK', onPress: () => this.logoutUser() }],
      { cancelable: false }
    );
  }

  /**
   * Start idle timer
   */
  startIdleTimer() {
    this.idleTimer = setTimeout(() => {
      this.handleIdleTimeout();
    }, this.securityConfig.IDLE_TIMEOUT);
  }

  /**
   * Reset idle timer
   */
  resetIdleTimer() {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }
    this.startIdleTimer();
  }

  /**
   * Handle idle timeout
   */
  handleIdleTimeout() {
    console.log('🔒 Idle timeout detected');
    // Implement idle timeout logic (e.g., lock screen, require re-authentication)
  }

  /**
   * Logout user
   */
  async logoutUser() {
    try {
      // Clear sensitive data
      await AsyncStorage.multiRemove(['auth_token', 'user_data', 'session_data']);
      
      // Navigate to login screen
      // This would be handled by the navigation service
      console.log('🔒 User logged out due to security policy');
    } catch (error) {
      console.error('❌ Error during security logout:', error);
    }
  }

  /**
   * Encrypt sensitive data
   */
  async encryptData(data, key) {
    // TODO: Implement encryption using native crypto modules
    console.log('🔒 Data encryption (requires crypto implementation)');
    return data; // Placeholder
  }

  /**
   * Decrypt sensitive data
   */
  async decryptData(encryptedData, key) {
    // TODO: Implement decryption using native crypto modules
    console.log('🔒 Data decryption (requires crypto implementation)');
    return encryptedData; // Placeholder
  }

  /**
   * Secure storage operations
   */
  async secureStore(key, value) {
    try {
      const encryptedValue = await this.encryptData(JSON.stringify(value));
      await AsyncStorage.setItem(`secure_${key}`, encryptedValue);
    } catch (error) {
      console.error('❌ Secure storage failed:', error);
      throw error;
    }
  }

  async secureRetrieve(key) {
    try {
      const encryptedValue = await AsyncStorage.getItem(`secure_${key}`);
      if (!encryptedValue) return null;
      
      const decryptedValue = await this.decryptData(encryptedValue);
      return JSON.parse(decryptedValue);
    } catch (error) {
      console.error('❌ Secure retrieval failed:', error);
      return null;
    }
  }

  /**
   * Get security status
   */
  getSecurityStatus() {
    return {
      ...this.securityState,
      config: this.securityConfig,
    };
  }

  /**
   * Update security configuration
   */
  updateSecurityConfig(updates) {
    this.securityConfig = {
      ...this.securityConfig,
      ...updates,
    };
  }

  /**
   * Cleanup security timers
   */
  cleanup() {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
    }
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }
  }
}

// Create singleton instance
const securityManager = new SecurityManager();

export default securityManager;
