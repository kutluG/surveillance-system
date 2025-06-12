import React, {createContext, useContext, useState, useEffect} from 'react';
import secureStorage from '../utils/secureStorage';
import {authService} from '../services/authService';
import biometricService from '../services/biometricService';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({children}) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
  }, []);
  const checkAuthState = async () => {
    try {
      const token = await secureStorage.getItem('auth_token');
      if (token) {
        const userData = await authService.verifyToken(token);
        if (userData) {
          setUser(userData);
          setIsAuthenticated(true);
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      await secureStorage.removeItem('auth_token');
    } finally {
      setLoading(false);
    }
  };  const login = async (credentials) => {
    try {
      setLoading(true);
      const response = await authService.login(credentials);
      
      await secureStorage.setItem('auth_token', response.token);
      setUser(response.user);
      setIsAuthenticated(true);
      
      // Prompt for biometric setup on successful login
      biometricService.promptForBiometricSetup();
      
      return response;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const loginWithBiometric = async () => {
    try {
      setLoading(true);
      
      const biometricResult = await biometricService.authenticateWithBiometric(
        'Authenticate to access your surveillance system'
      );
      
      if (!biometricResult.success) {
        throw new Error(biometricResult.error || 'Biometric authentication failed');
      }
        // Get stored token for biometric login
      const token = await secureStorage.getItem('auth_token');
      if (!token) {
        throw new Error('No stored authentication found. Please login with credentials.');
      }
      
      const userData = await authService.verifyToken(token);
      if (!userData) {
        throw new Error('Authentication token is no longer valid. Please login again.');
      }
      
      setUser(userData);
      setIsAuthenticated(true);
      
      return { success: true, user: userData };
    } catch (error) {
      console.error('Biometric login failed:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };
  const logout = async () => {
    try {
      await secureStorage.removeItem('auth_token');
      setUser(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    login,
    loginWithBiometric,
    logout,
    checkAuthState,
    biometricService,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
