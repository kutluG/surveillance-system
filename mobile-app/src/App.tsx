import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import { StatusBar, StyleSheet, View, Text, Animated } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { store } from './store';
import AppNavigator from './navigation/AppNavigator';
import { AuthProvider } from './contexts/AuthContext';
import { NetworkProvider, useNetworkStatus } from './contexts/NetworkProvider';
import NotificationManager from './components/NotificationManager';
import ErrorBoundary from './components/ErrorBoundary';
import realTimeIntegration from './services/realTimeIntegration';
import ConfigValidator from './utils/configValidator';
import EnvironmentConfig from './config/environment';
import securityManager from './security/securityManager';
import performanceMonitor from './utils/performanceMonitor';
import secureStorage from './utils/secureStorage';

// Offline Banner Component
const OfflineBanner: React.FC = () => {
  const { isConnected } = useNetworkStatus();
  const [bannerHeight] = React.useState(new Animated.Value(0));

  useEffect(() => {
    Animated.timing(bannerHeight, {
      toValue: isConnected ? 0 : 60,
      duration: 300,
      useNativeDriver: false,
    }).start();
  }, [isConnected, bannerHeight]);

  if (isConnected) {
    return null;
  }

  return (
    <Animated.View style={[styles.offlineBanner, { height: bannerHeight }]}>
      <View style={styles.bannerContent}>
        <Text style={styles.bannerIcon}>⚠️</Text>
        <View style={styles.bannerTextContainer}>
          <Text style={styles.bannerText}>No Internet Connection</Text>
          <Text style={styles.bannerSubText}>Working in offline mode</Text>
        </View>
      </View>
    </Animated.View>
  );
};

// Main App Content Component
const AppContent: React.FC = () => {
  useEffect(() => {
    // Initialize app
    const initializeApp = async () => {
      const appStartTime = Date.now();
        try {
        // Initialize performance monitoring
        console.log('📊 Starting performance monitoring...');
        
        // Initialize secure storage first (required for other services)
        console.log('🔐 Initializing secure storage...');
        await secureStorage.initialize();
        
        // Initialize security manager
        const securityInitialized = await securityManager.initializeSecurity();
        if (!securityInitialized) {
          console.error('❌ Security initialization failed - app may not be secure');
        }
        
        // Validate configuration in development
        if (EnvironmentConfig.isDevelopment()) {
          await ConfigValidator.validateAll();
        }
        
        // Initialize real-time integration
        await realTimeIntegration.initialize();
        
        // Record app startup time
        performanceMonitor.recordScreenLoad('App', appStartTime);
        
        console.log(`🚀 App initialized in ${EnvironmentConfig.getEnvironment()} mode`);
      } catch (error) {
        console.error('❌ App initialization failed:', error);
        
        // Record initialization error
        performanceMonitor.recordPerformanceIssue('app_initialization_error', {
          error: error.message,
          stack: error.stack,
        });
      }
    };

    initializeApp();
    
    return () => {
      // Cleanup on app unmount
      console.log('🧹 Cleaning up app resources...');
      realTimeIntegration.cleanup();
      securityManager.cleanup();
      performanceMonitor.stopMonitoring();
    };
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar 
        barStyle="light-content" 
        backgroundColor="#1a1a2e"
        translucent 
      />
      <OfflineBanner />
      <NavigationContainer>
        <AppNavigator />
        <NotificationManager />
      </NavigationContainer>
    </View>
  );
};

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <SafeAreaProvider>
          <AuthProvider>
            <NetworkProvider>
              <AppContent />
            </NetworkProvider>
          </AuthProvider>
        </SafeAreaProvider>
      </Provider>
    </ErrorBoundary>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  offlineBanner: {
    backgroundColor: '#ff6b6b',
    zIndex: 1000,
    elevation: 1000,
    overflow: 'hidden',
  },
  bannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    height: 60,
  },
  bannerIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  bannerTextContainer: {
    flex: 1,
  },
  bannerText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  bannerSubText: {
    color: '#ffffff',
    fontSize: 12,
    opacity: 0.9,
  },
});

export default App;
