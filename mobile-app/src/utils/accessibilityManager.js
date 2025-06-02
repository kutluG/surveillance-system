/**
 * Accessibility Manager
 * Enhances mobile app accessibility features for users with disabilities
 */

import { AccessibilityInfo, Alert, Vibration } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import performanceMonitor from './performanceMonitor';

class AccessibilityManager {
  constructor() {
    this.isScreenReaderEnabled = false;
    this.preferences = {
      reduceMotion: false,
      highContrast: false,
      largeText: false,
      voiceAnnouncements: true,
      hapticFeedback: true,
      slowAnimations: false,
    };
    
    this.initialized = false;
    this.announcements = [];
    
    // Accessibility constants
    this.ANNOUNCEMENT_DELAY = 500; // ms
    this.VIBRATION_PATTERNS = {
      success: [100, 50, 100],
      error: [200, 100, 200, 100, 200],
      warning: [150, 75, 150],
      notification: [50, 25, 50],
    };
  }

  /**
   * Initialize accessibility features
   */
  async initialize() {
    if (this.initialized) return;
    
    try {
      console.log('♿ Initializing accessibility features...');
      
      // Check if screen reader is enabled
      this.isScreenReaderEnabled = await AccessibilityInfo.isScreenReaderEnabled();
      
      // Load user preferences
      await this.loadPreferences();
      
      // Set up accessibility listeners
      this.setupAccessibilityListeners();
      
      // Configure accessibility settings
      this.applyAccessibilitySettings();
      
      this.initialized = true;
      
      // Announce successful initialization
      if (this.isScreenReaderEnabled) {
        this.announce('Surveillance app accessibility features enabled');
      }
      
      console.log('♿ Accessibility features initialized');
      
      // Record initialization
      performanceMonitor.recordUserInteraction('accessibility_initialized', 'AccessibilityManager', {
        screenReaderEnabled: this.isScreenReaderEnabled,
        preferences: this.preferences,
      });
      
    } catch (error) {
      console.error('❌ Failed to initialize accessibility features:', error);
      throw error;
    }
  }

  /**
   * Set up accessibility event listeners
   */
  setupAccessibilityListeners() {
    // Listen for screen reader state changes
    AccessibilityInfo.addEventListener('screenReaderChanged', (isEnabled) => {
      console.log(`♿ Screen reader ${isEnabled ? 'enabled' : 'disabled'}`);
      this.isScreenReaderEnabled = isEnabled;
      
      if (isEnabled) {
        this.announce('Screen reader activated');
      }
      
      // Record state change
      performanceMonitor.recordUserInteraction('screen_reader_changed', 'AccessibilityManager', {
        enabled: isEnabled,
      });
    });

    // Listen for reduce motion changes
    AccessibilityInfo.addEventListener('reduceMotionChanged', (reduceMotion) => {
      console.log(`♿ Reduce motion ${reduceMotion ? 'enabled' : 'disabled'}`);
      this.preferences.reduceMotion = reduceMotion;
      this.savePreferences();
      
      // Apply motion settings
      this.applyMotionSettings();
    });
  }

  /**
   * Load accessibility preferences from storage
   */
  async loadPreferences() {
    try {
      const stored = await AsyncStorage.getItem('@accessibility_preferences');
      if (stored) {
        this.preferences = { ...this.preferences, ...JSON.parse(stored) };
        console.log('♿ Accessibility preferences loaded:', this.preferences);
      }
    } catch (error) {
      console.error('❌ Failed to load accessibility preferences:', error);
    }
  }

  /**
   * Save accessibility preferences to storage
   */
  async savePreferences() {
    try {
      await AsyncStorage.setItem('@accessibility_preferences', JSON.stringify(this.preferences));
      console.log('♿ Accessibility preferences saved');
    } catch (error) {
      console.error('❌ Failed to save accessibility preferences:', error);
    }
  }

  /**
   * Apply accessibility settings
   */
  applyAccessibilitySettings() {
    // Apply motion settings
    this.applyMotionSettings();
    
    // Apply contrast settings
    this.applyContrastSettings();
    
    // Apply text size settings
    this.applyTextSettings();
    
    console.log('♿ Accessibility settings applied');
  }

  /**
   * Apply motion and animation settings
   */
  applyMotionSettings() {
    if (this.preferences.reduceMotion || this.preferences.slowAnimations) {
      // Note: This would typically be handled by the app's animation system
      console.log('♿ Motion settings applied - animations reduced');
    }
  }

  /**
   * Apply contrast settings
   */
  applyContrastSettings() {
    if (this.preferences.highContrast) {
      // Note: This would typically update the app's theme
      console.log('♿ High contrast mode applied');
    }
  }

  /**
   * Apply text size settings
   */
  applyTextSettings() {
    if (this.preferences.largeText) {
      // Note: This would typically update font sizes throughout the app
      console.log('♿ Large text mode applied');
    }
  }

  /**
   * Announce text to screen reader
   */
  announce(message, priority = 'polite') {
    if (!this.isScreenReaderEnabled || !this.preferences.voiceAnnouncements) {
      return;
    }

    // Queue announcement to avoid overlapping
    this.announcements.push({ message, priority, timestamp: Date.now() });
    
    // Process announcements after delay
    setTimeout(() => {
      this.processNextAnnouncement();
    }, this.ANNOUNCEMENT_DELAY);
  }

  /**
   * Process queued announcements
   */
  processNextAnnouncement() {
    if (this.announcements.length === 0) return;
    
    const announcement = this.announcements.shift();
    
    try {
      AccessibilityInfo.announceForAccessibility(announcement.message);
      console.log(`♿ Announced: "${announcement.message}"`);
      
      // Record announcement
      performanceMonitor.recordUserInteraction('accessibility_announcement', 'AccessibilityManager', {
        message: announcement.message,
        priority: announcement.priority,
      });
      
    } catch (error) {
      console.error('❌ Failed to make accessibility announcement:', error);
    }
  }

  /**
   * Provide haptic feedback
   */
  hapticFeedback(type = 'notification') {
    if (!this.preferences.hapticFeedback) return;
    
    try {
      const pattern = this.VIBRATION_PATTERNS[type] || this.VIBRATION_PATTERNS.notification;
      Vibration.vibrate(pattern);
      
      console.log(`♿ Haptic feedback: ${type}`);
      
      // Record haptic feedback
      performanceMonitor.recordUserInteraction('haptic_feedback', 'AccessibilityManager', {
        type,
        pattern: pattern.join(','),
      });
      
    } catch (error) {
      console.error('❌ Failed to provide haptic feedback:', error);
    }
  }

  /**
   * Create accessible button props
   */
  createAccessibleButton(label, hint = '', role = 'button') {
    return {
      accessible: true,
      accessibilityLabel: label,
      accessibilityHint: hint,
      accessibilityRole: role,
      onPress: () => {
        this.hapticFeedback('notification');
        this.announce(`${label} activated`);
      },
    };
  }

  /**
   * Create accessible form field props
   */
  createAccessibleFormField(label, value, error = null, required = false) {
    const accessibilityLabel = required ? `${label}, required` : label;
    const accessibilityValue = { text: value || 'empty' };
    const accessibilityState = { 
      invalid: !!error,
      required,
    };
    
    let accessibilityHint = 'Double tap to edit';
    if (error) {
      accessibilityHint += `. Error: ${error}`;
    }
    
    return {
      accessible: true,
      accessibilityLabel,
      accessibilityValue,
      accessibilityState,
      accessibilityHint,
      accessibilityRole: 'textinput',
    };
  }

  /**
   * Create accessible navigation props
   */
  createAccessibleNavigation(screenName, isActive = false) {
    return {
      accessible: true,
      accessibilityLabel: `Navigate to ${screenName}`,
      accessibilityHint: isActive ? 'Currently selected' : 'Double tap to navigate',
      accessibilityRole: 'tab',
      accessibilityState: { selected: isActive },
    };
  }

  /**
   * Create accessible alert props
   */
  createAccessibleAlert(severity, message) {
    const severityLabels = {
      low: 'Low priority alert',
      medium: 'Medium priority alert',
      high: 'High priority alert',
      critical: 'Critical alert',
    };
    
    return {
      accessible: true,
      accessibilityLabel: severityLabels[severity] || 'Alert',
      accessibilityValue: { text: message },
      accessibilityRole: 'alert',
      accessibilityLiveRegion: severity === 'critical' ? 'assertive' : 'polite',
    };
  }

  /**
   * Handle camera view accessibility
   */
  createAccessibleCameraView(detections = []) {
    let description = 'Camera view';
    
    if (detections.length > 0) {
      const detectionTypes = detections.map(d => d.type).join(', ');
      description += `. Detected: ${detectionTypes}`;
    } else {
      description += '. No detections';
    }
    
    return {
      accessible: true,
      accessibilityLabel: description,
      accessibilityRole: 'image',
      accessibilityHint: 'Live camera feed',
    };
  }

  /**
   * Update user preference
   */
  async updatePreference(key, value) {
    if (!(key in this.preferences)) {
      throw new Error(`Invalid preference key: ${key}`);
    }
    
    this.preferences[key] = value;
    await this.savePreferences();
    
    // Apply settings if needed
    this.applyAccessibilitySettings();
    
    // Announce change
    this.announce(`${key} ${value ? 'enabled' : 'disabled'}`);
    
    console.log(`♿ Preference updated: ${key} = ${value}`);
    
    // Record preference change
    performanceMonitor.recordUserInteraction('accessibility_preference_changed', 'AccessibilityManager', {
      key,
      value,
    });
  }

  /**
   * Get current preferences
   */
  getPreferences() {
    return { ...this.preferences };
  }

  /**
   * Check if accessibility feature is enabled
   */
  isFeatureEnabled(feature) {
    return this.preferences[feature] || false;
  }

  /**
   * Get accessibility status summary
   */
  getAccessibilityStatus() {
    return {
      initialized: this.initialized,
      screenReaderEnabled: this.isScreenReaderEnabled,
      preferences: this.preferences,
      queuedAnnouncements: this.announcements.length,
    };
  }

  /**
   * Handle emergency accessibility announcement
   */
  emergencyAnnouncement(message) {
    // Clear queue and announce immediately
    this.announcements = [];
    
    try {
      AccessibilityInfo.announceForAccessibility(message);
      this.hapticFeedback('error');
      
      console.log(`🚨 Emergency announcement: "${message}"`);
      
      // Record emergency announcement
      performanceMonitor.recordUserInteraction('emergency_announcement', 'AccessibilityManager', {
        message,
      });
      
    } catch (error) {
      console.error('❌ Failed to make emergency announcement:', error);
      
      // Fallback to alert if screen reader fails
      Alert.alert('Emergency Alert', message);
    }
  }

  /**
   * Cleanup accessibility features
   */
  cleanup() {
    if (!this.initialized) return;
    
    console.log('♿ Cleaning up accessibility features...');
    
    // Remove event listeners
    AccessibilityInfo.removeEventListener('screenReaderChanged');
    AccessibilityInfo.removeEventListener('reduceMotionChanged');
    
    // Clear announcements
    this.announcements = [];
    
    this.initialized = false;
    
    console.log('♿ Accessibility cleanup completed');
  }
}

// Accessibility helper functions
export const createAccessibilityProps = (accessibilityManager, type, options = {}) => {
  switch (type) {
    case 'button':
      return accessibilityManager.createAccessibleButton(
        options.label,
        options.hint,
        options.role
      );
    case 'form-field':
      return accessibilityManager.createAccessibleFormField(
        options.label,
        options.value,
        options.error,
        options.required
      );
    case 'navigation':
      return accessibilityManager.createAccessibleNavigation(
        options.screenName,
        options.isActive
      );
    case 'alert':
      return accessibilityManager.createAccessibleAlert(
        options.severity,
        options.message
      );
    case 'camera':
      return accessibilityManager.createAccessibleCameraView(
        options.detections
      );
    default:
      return {};
  }
};

// Export singleton instance
const accessibilityManager = new AccessibilityManager();
export default accessibilityManager;
