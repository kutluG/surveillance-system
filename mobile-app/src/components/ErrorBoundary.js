import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { COLORS, SIZES, FONTS } from '../constants';
import performanceMonitor from '../utils/performanceMonitor';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      errorId: Date.now().toString(),
    };
  }
  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('🚨 ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Record error in performance monitoring
    performanceMonitor.recordPerformanceIssue('component_error', {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      errorBoundary: this.props.name || 'ErrorBoundary',
    });

    // Persist error for crash recovery
    this.persistError(error, errorInfo);

    // Report error to crash reporting service
    this.reportError(error, errorInfo);
  }

  async persistError(error, errorInfo) {
    try {
      const errorReport = {
        timestamp: Date.now(),
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name,
        },
        errorInfo: {
          componentStack: errorInfo.componentStack,
        },
        appState: {
          route: this.props.currentRoute || 'unknown',
          user: this.props.userId || 'anonymous',
          environment: __DEV__ ? 'development' : 'production',
        },
      };
      
      const existingErrors = await AsyncStorage.getItem('@error_reports');
      const errors = existingErrors ? JSON.parse(existingErrors) : [];
      
      errors.push(errorReport);
      
      // Keep only last 10 errors
      if (errors.length > 10) {
        errors.splice(0, errors.length - 10);
      }
      
      await AsyncStorage.setItem('@error_reports', JSON.stringify(errors));
      console.log('💾 Error report saved to storage');
    } catch (persistError) {
      console.error('❌ Failed to persist error:', persistError);
    }
  }

  reportError = async (error, errorInfo) => {
    try {
      // This would integrate with your crash reporting service
      const errorReport = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        errorId: this.state.errorId,
        userId: this.props.userId || 'anonymous',
        appVersion: '1.0.0',
        platform: 'mobile',
      };

      console.log('Error Report:', errorReport);
      
      // Send to backend error tracking
      // await this.sendErrorReport(errorReport);
    } catch (reportError) {
      console.error('Failed to report error:', reportError);
    }
  };
  handleRetry = () => {
    console.log('🔄 Retrying after error...');
    
    // Record retry attempt
    performanceMonitor.recordUserInteraction('error_retry', 'ErrorBoundary', {
      errorId: this.state.errorId,
      errorMessage: this.state.error?.message,
    });
    
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
    });

    // Call custom retry handler if provided
    if (this.props.onRetry) {
      this.props.onRetry();
    }  };

  handleRestart = () => {
    // Clear any cached data and restart the app
    Alert.alert(
      'Restart App',
      'This will clear the app cache and restart. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Restart', 
          onPress: () => {
            // Clear cache and restart
            this.clearCacheAndRestart();
          }
        },
      ]
    );
  };

  clearCacheAndRestart = async () => {
    try {
      // Clear AsyncStorage
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      await AsyncStorage.clear();
      
      // Restart app
      const RNRestart = require('react-native-restart').default;
      RNRestart.Restart();
    } catch (error) {
      console.error('Failed to clear cache and restart:', error);
    }
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;
      const isDevelopment = __DEV__;

      return (
        <View style={styles.container}>
          <ScrollView 
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
          >
            <View style={styles.header}>
              <Icon name="error-outline" size={64} color={COLORS.error} />
              <Text style={styles.title}>Oops! Something went wrong</Text>
              <Text style={styles.subtitle}>
                We apologize for the inconvenience. The app encountered an unexpected error.
              </Text>
            </View>

            <View style={styles.actions}>
              <TouchableOpacity
                style={[styles.button, styles.primaryButton]}
                onPress={this.handleRetry}
              >
                <Icon name="refresh" size={20} color={COLORS.white} />
                <Text style={styles.primaryButtonText}>Try Again</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.button, styles.secondaryButton]}
                onPress={this.handleRestart}
              >
                <Icon name="restart-alt" size={20} color={COLORS.primary} />
                <Text style={styles.secondaryButtonText}>Restart App</Text>
              </TouchableOpacity>
            </View>

            {isDevelopment && error && (
              <View style={styles.debugSection}>
                <Text style={styles.debugTitle}>Debug Information</Text>
                
                <View style={styles.debugContent}>
                  <Text style={styles.debugLabel}>Error Message:</Text>
                  <Text style={styles.debugText}>{error.message}</Text>
                  
                  {error.stack && (
                    <>
                      <Text style={styles.debugLabel}>Stack Trace:</Text>
                      <Text style={styles.debugText}>{error.stack}</Text>
                    </>
                  )}
                  
                  {errorInfo && errorInfo.componentStack && (
                    <>
                      <Text style={styles.debugLabel}>Component Stack:</Text>
                      <Text style={styles.debugText}>{errorInfo.componentStack}</Text>
                    </>
                  )}
                </View>
              </View>
            )}

            <View style={styles.footer}>
              <Text style={styles.footerText}>
                Error ID: {this.state.errorId}
              </Text>
              <Text style={styles.footerText}>
                If this problem persists, please contact support.
              </Text>
            </View>
          </ScrollView>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: SIZES.padding * 2,
  },
  header: {
    alignItems: 'center',
    marginBottom: SIZES.padding * 2,
  },
  title: {
    ...FONTS.h1,
    color: COLORS.text,
    textAlign: 'center',
    marginTop: SIZES.padding,
    marginBottom: SIZES.base,
  },
  subtitle: {
    ...FONTS.body3,
    color: COLORS.gray,
    textAlign: 'center',
    lineHeight: 22,
  },
  actions: {
    marginBottom: SIZES.padding * 2,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: SIZES.padding,
    paddingHorizontal: SIZES.padding * 2,
    borderRadius: SIZES.radius,
    marginBottom: SIZES.base,
  },
  primaryButton: {
    backgroundColor: COLORS.primary,
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: COLORS.primary,
  },
  primaryButtonText: {
    ...FONTS.h3,
    color: COLORS.white,
    marginLeft: SIZES.base,
  },
  secondaryButtonText: {
    ...FONTS.h3,
    color: COLORS.primary,
    marginLeft: SIZES.base,
  },
  debugSection: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    marginBottom: SIZES.padding,
  },
  debugTitle: {
    ...FONTS.h3,
    color: COLORS.text,
    marginBottom: SIZES.base,
  },
  debugContent: {
    maxHeight: 300,
  },
  debugLabel: {
    ...FONTS.body4,
    color: COLORS.primary,
    fontWeight: 'bold',
    marginTop: SIZES.base,
    marginBottom: SIZES.base / 2,
  },
  debugText: {
    ...FONTS.caption,
    color: COLORS.gray,
    fontFamily: 'monospace',
    lineHeight: 16,
  },
  footer: {
    alignItems: 'center',
  },
  footerText: {
    ...FONTS.caption,
    color: COLORS.gray,
    textAlign: 'center',
    marginBottom: SIZES.base / 2,
  },
});

// HOC for wrapping components with error boundary
export const withErrorBoundary = (WrappedComponent, errorBoundaryProps = {}) => {
  return React.forwardRef((props, ref) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} ref={ref} />
    </ErrorBoundary>
  ));
};

// Utility function to clear stored error reports
export const clearErrorReports = async () => {
  try {
    await AsyncStorage.removeItem('@error_reports');
    console.log('🧹 Error reports cleared');
  } catch (error) {
    console.error('❌ Failed to clear error reports:', error);
  }
};

// Utility function to get stored error reports
export const getErrorReports = async () => {
  try {
    const reports = await AsyncStorage.getItem('@error_reports');
    return reports ? JSON.parse(reports) : [];
  } catch (error) {
    console.error('❌ Failed to get error reports:', error);
    return [];
  }
};

export default ErrorBoundary;
