import React, { useEffect } from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {Provider} from 'react-redux';
import {StatusBar, StyleSheet} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';

import {store} from './store';
import AppNavigator from './navigation/AppNavigator';
import {AuthProvider} from './contexts/AuthContext';
import {NetworkProvider} from './contexts/NetworkContext';
import NotificationManager from './components/NotificationManager';
import ErrorBoundary from './components/ErrorBoundary';
import realTimeIntegration from './services/realTimeIntegration';
import ConfigValidator from './utils/configValidator';
import EnvironmentConfig from './config/environment';
import securityManager from './security/securityManager';
import performanceMonitor from './utils/performanceMonitor';

const App = () => {  useEffect(() => {
    // Initialize app
    const initializeApp = async () => {
      const appStartTime = Date.now();
      
      try {
        // Initialize performance monitoring
        console.log('📊 Starting performance monitoring...');
        
        // Initialize security manager first
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
    <ErrorBoundary>
      <Provider store={store}>
        <SafeAreaProvider>
          <AuthProvider>
            <NetworkProvider>
              <NavigationContainer>
                <StatusBar 
                  barStyle="light-content" 
                  backgroundColor="#1a1a2e"
                  translucent 
                />
                <AppNavigator />
                <NotificationManager />
              </NavigationContainer>
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
});

export default App;
