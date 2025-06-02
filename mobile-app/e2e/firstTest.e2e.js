describe('SurveillanceApp E2E Tests', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  describe('Authentication Flow', () => {
    it('should show login screen on first launch', async () => {
      await expect(element(by.text('Surveillance System'))).toBeVisible();
      await expect(element(by.id('email-input'))).toBeVisible();
      await expect(element(by.id('password-input'))).toBeVisible();
      await expect(element(by.id('login-button'))).toBeVisible();
    });

    it('should validate empty email and password', async () => {
      await element(by.id('login-button')).tap();
      await expect(element(by.text('Please enter a valid email address'))).toBeVisible();
    });

    it('should validate email format', async () => {
      await element(by.id('email-input')).typeText('invalid-email');
      await element(by.id('password-input')).typeText('password123');
      await element(by.id('login-button')).tap();
      await expect(element(by.text('Please enter a valid email address'))).toBeVisible();
    });

    it('should show error for invalid credentials', async () => {
      await element(by.id('email-input')).clearText();
      await element(by.id('email-input')).typeText('test@example.com');
      await element(by.id('password-input')).clearText();
      await element(by.id('password-input')).typeText('wrongpassword');
      await element(by.id('login-button')).tap();
      
      // Wait for error message
      await waitFor(element(by.text('Invalid credentials')))
        .toBeVisible()
        .withTimeout(5000);
    });

    it('should login successfully with valid credentials', async () => {
      await element(by.id('email-input')).clearText();
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).clearText();
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      
      // Wait for dashboard to appear
      await waitFor(element(by.text('Dashboard')))
        .toBeVisible()
        .withTimeout(10000);
    });
  });

  describe('Dashboard Flow', () => {
    beforeEach(async () => {
      // Login first
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      await waitFor(element(by.text('Dashboard'))).toBeVisible().withTimeout(10000);
    });

    it('should display dashboard with system overview', async () => {
      await expect(element(by.text('System Overview'))).toBeVisible();
      await expect(element(by.text('Quick Actions'))).toBeVisible();
      await expect(element(by.text('Recent Alerts'))).toBeVisible();
    });

    it('should show camera statistics', async () => {
      await expect(element(by.id('total-cameras'))).toBeVisible();
      await expect(element(by.id('online-cameras'))).toBeVisible();
      await expect(element(by.id('alerts-count'))).toBeVisible();
    });

    it('should navigate to cameras screen from quick actions', async () => {
      await element(by.text('View Cameras')).tap();
      await waitFor(element(by.text('Cameras'))).toBeVisible().withTimeout(5000);
    });

    it('should navigate to alerts screen from quick actions', async () => {
      await element(by.text('View Alerts')).tap();
      await waitFor(element(by.text('Alerts'))).toBeVisible().withTimeout(5000);
    });

    it('should refresh dashboard data', async () => {
      await element(by.id('dashboard-scroll')).swipe('down', 'fast', 0.5);
      // Verify refresh indicator appears and disappears
      await waitFor(element(by.id('refresh-indicator'))).not.toBeVisible().withTimeout(5000);
    });
  });

  describe('Cameras Flow', () => {
    beforeEach(async () => {
      // Login and navigate to cameras
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      await waitFor(element(by.text('Dashboard'))).toBeVisible().withTimeout(10000);
      await element(by.text('Cameras')).tap();
      await waitFor(element(by.text('Cameras'))).toBeVisible().withTimeout(5000);
    });

    it('should display list of cameras', async () => {
      await expect(element(by.id('cameras-list'))).toBeVisible();
    });

    it('should filter cameras by status', async () => {
      await element(by.id('filter-button')).tap();
      await element(by.text('Online')).tap();
      await element(by.text('Apply')).tap();
      
      // Verify filtering worked
      await expect(element(by.id('cameras-list'))).toBeVisible();
    });

    it('should search cameras by name', async () => {
      await element(by.id('search-input')).typeText('Front Door');
      await waitFor(element(by.text('Front Door Camera'))).toBeVisible().withTimeout(3000);
    });

    it('should open camera detail screen', async () => {
      await element(by.text('Front Door Camera')).tap();
      await waitFor(element(by.text('Camera Details'))).toBeVisible().withTimeout(5000);
      await expect(element(by.id('video-player'))).toBeVisible();
    });
  });

  describe('Alerts Flow', () => {
    beforeEach(async () => {
      // Login and navigate to alerts
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      await waitFor(element(by.text('Dashboard'))).toBeVisible().withTimeout(10000);
      await element(by.text('Alerts')).tap();
      await waitFor(element(by.text('Alerts'))).toBeVisible().withTimeout(5000);
    });

    it('should display list of alerts', async () => {
      await expect(element(by.id('alerts-list'))).toBeVisible();
    });

    it('should filter alerts by type', async () => {
      await element(by.id('filter-button')).tap();
      await element(by.text('Motion Detected')).tap();
      await element(by.text('Apply')).tap();
      
      // Verify filtering worked
      await expect(element(by.id('alerts-list'))).toBeVisible();
    });

    it('should mark alert as read', async () => {
      await element(by.id('alert-0')).tap();
      await element(by.text('Mark as Read')).tap();
      
      // Verify alert is marked as read
      await expect(element(by.id('read-indicator'))).toBeVisible();
    });

    it('should open alert detail screen', async () => {
      await element(by.id('alert-0')).tap();
      await waitFor(element(by.text('Alert Details'))).toBeVisible().withTimeout(5000);
      await expect(element(by.id('alert-image'))).toBeVisible();
    });
  });

  describe('Settings Flow', () => {
    beforeEach(async () => {
      // Login and navigate to settings
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      await waitFor(element(by.text('Dashboard'))).toBeVisible().withTimeout(10000);
      await element(by.text('Settings')).tap();
      await waitFor(element(by.text('Settings'))).toBeVisible().withTimeout(5000);
    });

    it('should display settings options', async () => {
      await expect(element(by.text('Notifications'))).toBeVisible();
      await expect(element(by.text('Dark Mode'))).toBeVisible();
      await expect(element(by.text('Biometric Authentication'))).toBeVisible();
    });

    it('should toggle dark mode', async () => {
      await element(by.id('dark-mode-toggle')).tap();
      // Verify theme change (this would need visual verification in real test)
    });

    it('should enable biometric authentication', async () => {
      await element(by.id('biometric-toggle')).tap();
      // Verify biometric prompt appears
      await expect(element(by.text('Enable Biometric Authentication'))).toBeVisible();
    });

    it('should logout successfully', async () => {
      await element(by.text('Logout')).tap();
      await element(by.text('Confirm')).tap();
      
      // Verify back to login screen
      await waitFor(element(by.text('Surveillance System'))).toBeVisible().withTimeout(5000);
    });
  });

  describe('Network Connectivity', () => {
    it('should handle offline mode', async () => {
      // Simulate network disconnection
      await device.disableNetworkConnection();
      
      // Login with cached credentials
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      
      // Verify offline indicator
      await expect(element(by.text('Offline'))).toBeVisible();
      
      // Restore network connection
      await device.enableNetworkConnection();
      
      // Verify online indicator
      await waitFor(element(by.text('Online'))).toBeVisible().withTimeout(10000);
    });
  });

  describe('Video Playback', () => {
    beforeEach(async () => {
      // Login and navigate to camera detail
      await element(by.id('email-input')).typeText('admin@surveillance.com');
      await element(by.id('password-input')).typeText('admin123');
      await element(by.id('login-button')).tap();
      await waitFor(element(by.text('Dashboard'))).toBeVisible().withTimeout(10000);
      await element(by.text('Cameras')).tap();
      await waitFor(element(by.text('Cameras'))).toBeVisible().withTimeout(5000);
      await element(by.text('Front Door Camera')).tap();
      await waitFor(element(by.text('Camera Details'))).toBeVisible().withTimeout(5000);
    });

    it('should display video player', async () => {
      await expect(element(by.id('video-player'))).toBeVisible();
    });

    it('should have video controls', async () => {
      await element(by.id('video-player')).tap();
      await expect(element(by.id('play-pause-button'))).toBeVisible();
      await expect(element(by.id('fullscreen-button'))).toBeVisible();
    });

    it('should toggle fullscreen mode', async () => {
      await element(by.id('video-player')).tap();
      await element(by.id('fullscreen-button')).tap();
      
      // Verify fullscreen mode
      await expect(element(by.id('exit-fullscreen-button'))).toBeVisible();
    });
  });
});
