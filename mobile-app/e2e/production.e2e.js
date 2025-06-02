import {test, expect} from 'detox';

describe('Production E2E Tests', () => {
  beforeAll(async () => {
    await device.launchApp({
      newInstance: true,
      permissions: {
        camera: 'YES',
        microphone: 'YES',
        location: 'inuse',
        notifications: 'YES',
      },
    });
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  describe('Authentication Flow', () => {
    test('should complete login flow successfully', async () => {
      // Test login screen appears
      await expect(element(by.id('login-screen'))).toBeVisible();
      
      // Test email input
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      
      // Test password input
      await element(by.id('password-input')).typeText('demo123');
      
      // Test login button
      await element(by.id('login-button')).tap();
      
      // Verify successful login
      await expect(element(by.id('dashboard-screen'))).toBeVisible();
    });

    test('should handle biometric authentication', async () => {
      // Skip if biometrics not available
      if (device.getPlatform() === 'ios') {
        await element(by.id('biometric-login-button')).tap();
        // Note: Actual biometric testing requires simulator setup
        await expect(element(by.text('Face ID'))).toBeVisible();
      }
    });

    test('should handle logout properly', async () => {
      await element(by.id('settings-tab')).tap();
      await element(by.id('logout-button')).tap();
      await expect(element(by.id('login-screen'))).toBeVisible();
    });
  });

  describe('Dashboard Functionality', () => {
    beforeEach(async () => {
      // Ensure logged in
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      await expect(element(by.id('dashboard-screen'))).toBeVisible();
    });

    test('should display system overview correctly', async () => {
      await expect(element(by.id('camera-count'))).toBeVisible();
      await expect(element(by.id('alert-count'))).toBeVisible();
      await expect(element(by.id('status-indicator'))).toBeVisible();
    });

    test('should navigate to cameras screen', async () => {
      await element(by.id('cameras-tab')).tap();
      await expect(element(by.id('cameras-screen'))).toBeVisible();
      await expect(element(by.id('camera-list'))).toBeVisible();
    });

    test('should navigate to alerts screen', async () => {
      await element(by.id('alerts-tab')).tap();
      await expect(element(by.id('alerts-screen'))).toBeVisible();
      await expect(element(by.id('alert-list'))).toBeVisible();
    });
  });

  describe('Camera Monitoring', () => {
    beforeEach(async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      await element(by.id('cameras-tab')).tap();
    });

    test('should display camera list', async () => {
      await expect(element(by.id('camera-list'))).toBeVisible();
      
      // Check if at least one camera is displayed
      await expect(element(by.id('camera-item-0')).atIndex(0)).toBeVisible();
    });

    test('should open camera detail view', async () => {
      await element(by.id('camera-item-0')).atIndex(0).tap();
      await expect(element(by.id('camera-detail-screen'))).toBeVisible();
      await expect(element(by.id('video-player'))).toBeVisible();
    });

    test('should handle video controls', async () => {
      await element(by.id('camera-item-0')).atIndex(0).tap();
      
      // Test play/pause functionality
      await element(by.id('play-pause-button')).tap();
      
      // Test fullscreen toggle
      await element(by.id('fullscreen-button')).tap();
      await expect(element(by.id('video-player-fullscreen'))).toBeVisible();
    });
  });

  describe('Alert Management', () => {
    beforeEach(async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      await element(by.id('alerts-tab')).tap();
    });

    test('should display alerts list', async () => {
      await expect(element(by.id('alerts-screen'))).toBeVisible();
      await expect(element(by.id('alert-list'))).toBeVisible();
    });

    test('should filter alerts by severity', async () => {
      await element(by.id('filter-button')).tap();
      await element(by.id('filter-high')).tap();
      await element(by.id('apply-filter')).tap();
      
      // Verify filtered results
      await expect(element(by.id('alert-list'))).toBeVisible();
    });

    test('should acknowledge alerts', async () => {
      if (await element(by.id('alert-item-0')).exists()) {
        await element(by.id('alert-item-0')).tap();
        await expect(element(by.id('alert-detail-screen'))).toBeVisible();
        
        await element(by.id('acknowledge-button')).tap();
        await expect(element(by.text('Alert acknowledged'))).toBeVisible();
      }
    });
  });

  describe('Settings and Configuration', () => {
    beforeEach(async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      await element(by.id('settings-tab')).tap();
    });

    test('should display settings options', async () => {
      await expect(element(by.id('settings-screen'))).toBeVisible();
      await expect(element(by.id('notification-settings'))).toBeVisible();
      await expect(element(by.id('security-settings'))).toBeVisible();
      await expect(element(by.id('app-settings'))).toBeVisible();
    });

    test('should toggle notification settings', async () => {
      await element(by.id('notification-settings')).tap();
      await element(by.id('push-notifications-toggle')).tap();
      
      // Verify setting saved
      await expect(element(by.id('settings-saved-message'))).toBeVisible();
    });

    test('should navigate to security settings', async () => {
      await element(by.id('security-settings')).tap();
      await expect(element(by.id('biometric-toggle'))).toBeVisible();
      await expect(element(by.id('auto-lock-setting'))).toBeVisible();
    });
  });

  describe('Offline Functionality', () => {
    test('should handle network disconnection gracefully', async () => {
      // Simulate network disconnection
      await device.setNetworkConnection(false);
      
      await element(by.id('cameras-tab')).tap();
      await expect(element(by.id('offline-indicator'))).toBeVisible();
      
      // Restore network
      await device.setNetworkConnection(true);
      await expect(element(by.id('offline-indicator'))).not.toBeVisible();
    });

    test('should sync data when connection restored', async () => {
      await device.setNetworkConnection(false);
      
      // Make some changes offline
      await element(by.id('settings-tab')).tap();
      await element(by.id('notification-settings')).tap();
      await element(by.id('push-notifications-toggle')).tap();
      
      // Restore connection
      await device.setNetworkConnection(true);
      
      // Verify sync occurs
      await expect(element(by.id('sync-indicator'))).toBeVisible();
    });
  });

  describe('Performance Tests', () => {
    test('should load dashboard within acceptable time', async () => {
      const startTime = Date.now();
      
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      
      await expect(element(by.id('dashboard-screen'))).toBeVisible();
      
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000); // 5 seconds max
    });

    test('should handle multiple rapid navigation changes', async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      
      // Rapid navigation test
      for (let i = 0; i < 5; i++) {
        await element(by.id('cameras-tab')).tap();
        await element(by.id('alerts-tab')).tap();
        await element(by.id('dashboard-tab')).tap();
      }
      
      await expect(element(by.id('dashboard-screen'))).toBeVisible();
    });
  });

  describe('Security Tests', () => {
    test('should auto-lock after timeout', async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      
      // Send app to background
      await device.sendToHome();
      
      // Wait for auto-lock timeout (simulate)
      await device.launchApp();
      
      // Should require re-authentication
      await expect(element(by.id('biometric-prompt'))).toBeVisible();
    });

    test('should protect sensitive data in app switcher', async () => {
      await element(by.id('email-input')).typeText('demo@surveillance-ai.com');
      await element(by.id('password-input')).typeText('demo123');
      await element(by.id('login-button')).tap();
      
      // Navigate to sensitive screen
      await element(by.id('cameras-tab')).tap();
      await element(by.id('camera-item-0')).atIndex(0).tap();
      
      // Send to background (triggers privacy screen)
      await device.sendToHome();
      
      // When returning, sensitive content should be hidden
      await device.launchApp();
      await expect(element(by.id('privacy-overlay'))).toBeVisible();
    });
  });
});
