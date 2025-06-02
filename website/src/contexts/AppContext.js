import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  // State management
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Real-time data state
  const [dashboardData, setDashboardData] = useState({
    stats: {
      activeCameras: 0,
      totalAlerts: 0,
      storageUsed: 0,
      systemUptime: 0
    },
    recentAlerts: [],
    systemStatus: {}
  });
  
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState({});
  const [settings, setSettings] = useState({});
  
  // WebSocket connection
  const [ws, setWs] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  // API Base URL - now properly configured for both development and production
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';
  const WEBSOCKET_URL = process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8002/ws';
  const IS_PRODUCTION = process.env.REACT_APP_ENV === 'production';

  // Initialize WebSocket connection
  useEffect(() => {
    if (isAuthenticated) {
      initializeWebSocket();
    }
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [isAuthenticated]);
  const initializeWebSocket = () => {
    try {
      const websocket = new WebSocket(WEBSOCKET_URL);
      
      websocket.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setWs(websocket);
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        setWs(null);
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (isAuthenticated) {
            initializeWebSocket();
          }
        }, 5000);
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
      
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setConnectionStatus('error');
    }
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'dashboard_update':
        setDashboardData(prev => ({ ...prev, ...data.payload }));
        break;
      
      case 'new_alert':
        setAlerts(prev => [data.payload, ...prev]);
        setDashboardData(prev => ({
          ...prev,
          recentAlerts: [data.payload, ...prev.recentAlerts.slice(0, 4)]
        }));
        toast.error(`New Alert: ${data.payload.message}`);
        break;
      
      case 'camera_status_update':
        setCameras(prev => prev.map(camera => 
          camera.id === data.payload.id ? { ...camera, ...data.payload } : camera
        ));
        break;
      
      case 'system_status_update':
        setDashboardData(prev => ({
          ...prev,
          systemStatus: { ...prev.systemStatus, ...data.payload }
        }));
        break;
      
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  };

  // API Functions
  const apiCall = async (endpoint, options = {}) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const config = {
        baseURL: API_BASE_URL,
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json',
          ...(user?.token && { 'Authorization': `Bearer ${user.token}` })
        },
        ...options
      };
      
      const response = await axios(endpoint, config);
      return response.data;
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.message || 'An error occurred';
      setError(errorMessage);
      toast.error(errorMessage);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Authentication functions
  const login = async (credentials) => {
    try {
      const response = await apiCall('/auth/login', {
        method: 'POST',
        data: credentials
      });
      
      const userData = response.user;
      setUser(userData);
      setIsAuthenticated(true);
      
      // Store token in localStorage
      localStorage.setItem('auth_token', userData.token);
      
      toast.success('Successfully logged in!');
      return userData;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('auth_token');
    
    if (ws) {
      ws.close();
    }
    
    toast.success('Successfully logged out!');
  };

  // Check for existing authentication on app load
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      // Verify token with backend
      verifyToken(token);
    }
  }, []);

  const verifyToken = async (token) => {
    try {
      const response = await apiCall('/auth/verify', {
        method: 'POST',
        data: { token }
      });
      
      if (response.valid) {
        setUser(response.user);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('auth_token');
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      localStorage.removeItem('auth_token');
    }
  };

  // Data fetching functions
  const fetchDashboardData = async () => {
    try {
      const data = await apiCall('/dashboard/stats');
      setDashboardData(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  const fetchCameras = async () => {
    try {
      const data = await apiCall('/cameras');
      setCameras(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch cameras:', error);
    }
  };

  const fetchAlerts = async (filters = {}) => {
    try {
      const queryParams = new URLSearchParams(filters).toString();
      const data = await apiCall(`/alerts?${queryParams}`);
      setAlerts(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const fetchAnalytics = async (period = '7d') => {
    try {
      const data = await apiCall(`/analytics?period=${period}`);
      setAnalytics(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const data = await apiCall('/settings');
      setSettings(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  };

  const updateSettings = async (newSettings) => {
    try {
      const data = await apiCall('/settings', {
        method: 'PUT',
        data: newSettings
      });
      setSettings(data);
      toast.success('Settings updated successfully!');
      return data;
    } catch (error) {
      console.error('Failed to update settings:', error);
      throw error;
    }
  };

  // Camera actions
  const updateCamera = async (cameraId, updates) => {
    try {
      const data = await apiCall(`/cameras/${cameraId}`, {
        method: 'PUT',
        data: updates
      });
      
      setCameras(prev => prev.map(camera => 
        camera.id === cameraId ? { ...camera, ...data } : camera
      ));
      
      toast.success('Camera updated successfully!');
      return data;
    } catch (error) {
      console.error('Failed to update camera:', error);
      throw error;
    }
  };

  // Alert actions
  const updateAlert = async (alertId, updates) => {
    try {
      const data = await apiCall(`/alerts/${alertId}`, {
        method: 'PUT',
        data: updates
      });
      
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId ? { ...alert, ...data } : alert
      ));
      
      toast.success('Alert updated successfully!');
      return data;
    } catch (error) {
      console.error('Failed to update alert:', error);
      throw error;
    }
  };

  const value = {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,
    dashboardData,
    cameras,
    alerts,
    analytics,
    settings,
    connectionStatus,
    
    // Actions
    login,
    logout,
    fetchDashboardData,
    fetchCameras,
    fetchAlerts,
    fetchAnalytics,
    fetchSettings,
    updateSettings,
    updateCamera,
    updateAlert,
    apiCall
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};
