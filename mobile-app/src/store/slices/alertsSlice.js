import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { alertService } from '../../services/alertService';
import secureStorage from '../../utils/secureStorage';

const PENDING_ACKS_KEY = 'pendingAcks';

// Helper function to store pending acknowledgments for offline sync
const storePendingAck = async (alertId) => {
  try {
    const existing = await secureStorage.getItem(PENDING_ACKS_KEY);
    const pendingAcks = existing ? JSON.parse(existing) : [];
    
    // Avoid duplicates
    if (!pendingAcks.find(ack => ack.alertId === alertId)) {
      pendingAcks.push({
        alertId,
        timestamp: new Date().toISOString(),
        retryCount: 0
      });
      await secureStorage.setItem(PENDING_ACKS_KEY, JSON.stringify(pendingAcks));
    }
  } catch (error) {
    console.error('Error storing pending acknowledgment:', error);
  }
};

// Helper function to remove acknowledged alert from pending queue
const removePendingAckFromStorage = async (alertId) => {
  try {
    const existing = await secureStorage.getItem(PENDING_ACKS_KEY);
    if (existing) {
      const pendingAcks = JSON.parse(existing);
      const filteredAcks = pendingAcks.filter(ack => ack.alertId !== alertId);
      await secureStorage.setItem(PENDING_ACKS_KEY, JSON.stringify(filteredAcks));
    }
  } catch (error) {
    console.error('Error removing pending acknowledgment:', error);
  }
};

// Async thunks
export const flushPendingAcks = createAsyncThunk(
  'alerts/flushPendingAcks',
  async (_, { rejectWithValue }) => {
    try {
      const existing = await secureStorage.getItem(PENDING_ACKS_KEY);
      if (!existing) return { processed: 0 };
      
      const pendingAcks = JSON.parse(existing);
      if (pendingAcks.length === 0) return { processed: 0 };
      
      const results = [];
      const maxRetries = 3;
      
      for (const pendingAck of pendingAcks) {
        if (pendingAck.retryCount >= maxRetries) {
          console.warn(`Max retries reached for alert ${pendingAck.alertId}`);
          continue;
        }
        
        try {
          const response = await alertService.acknowledgeAlert(pendingAck.alertId);
          results.push({
            alertId: pendingAck.alertId,
            success: true,
            data: response.data
          });
        } catch (error) {
          console.error(`Failed to sync acknowledgment for alert ${pendingAck.alertId}:`, error);
          // Increment retry count
          pendingAck.retryCount = (pendingAck.retryCount || 0) + 1;
          results.push({
            alertId: pendingAck.alertId,
            success: false,
            error: error.message,
            retryCount: pendingAck.retryCount
          });
        }
      }
      
      // Filter out successfully processed acknowledgments
      const remainingAcks = pendingAcks.filter(ack => {
        const result = results.find(r => r.alertId === ack.alertId);
        return !result?.success;
      });
      
      // Update pending queue
      await secureStorage.setItem(PENDING_ACKS_KEY, JSON.stringify(remainingAcks));
      
      return {
        processed: results.filter(r => r.success).length,
        failed: results.filter(r => !r.success).length,
        results
      };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const fetchAlerts = createAsyncThunk(
  'alerts/fetchAlerts',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await alertService.getAlerts(params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const acknowledgeAlert = createAsyncThunk(
  'alerts/acknowledgeAlert',
  async (alertId, { rejectWithValue, getState, dispatch }) => {
    try {
      // Check network connectivity
      const networkState = getState().network;
      const isConnected = networkState?.isConnected ?? true;
      
      if (!isConnected) {
        // Store for offline sync
        await storePendingAck(alertId);
        
        // Return optimistic update data
        return { 
          alertId, 
          acknowledgedAt: new Date().toISOString(),
          offline: true 
        };
      }
        // Online: make API call
      const response = await alertService.acknowledgeAlert(alertId);
      
      // Remove from pending queue if it was there
      await removePendingAckFromStorage(alertId);
      
      return { alertId, ...response.data };
    } catch (error) {
      // If API fails but we're online, still store for retry
      const networkState = getState().network;
      const isConnected = networkState?.isConnected ?? true;
      
      if (isConnected) {
        await storePendingAck(alertId);
        // Return optimistic update even on API failure for better UX
        return { 
          alertId, 
          acknowledgedAt: new Date().toISOString(),
          offline: true 
        };
      }
      
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const dismissAlert = createAsyncThunk(
  'alerts/dismissAlert',
  async (alertId, { rejectWithValue }) => {
    try {
      const response = await alertService.dismissAlert(alertId);
      return { alertId, ...response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchAlertDetails = createAsyncThunk(
  'alerts/fetchAlertDetails',
  async (alertId, { rejectWithValue }) => {
    try {
      const response = await alertService.getAlertDetails(alertId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  alerts: [],
  selectedAlert: null,
  unreadCount: 0,
  loading: false,
  error: null,
  lastUpdated: null,
  pendingAcks: [], // Track alerts with pending offline acknowledgments
  syncStatus: 'idle', // idle, syncing, error
  filters: {
    status: 'all', // all, active, acknowledged, dismissed
    severity: 'all', // all, critical, high, medium, low
    type: 'all', // all, motion, intrusion, face_detection, etc.
    dateRange: 'today' // today, week, month, all
  },
  sortBy: 'timestamp', // timestamp, severity, type
  sortOrder: 'desc' // asc, desc
};

const alertsSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    addAlert: (state, action) => {
      const newAlert = action.payload;
      state.alerts.unshift(newAlert);
      if (newAlert.status === 'active') {
        state.unreadCount += 1;
      }
    },
    updateAlert: (state, action) => {
      const index = state.alerts.findIndex(alert => alert.id === action.payload.id);
      if (index !== -1) {
        const oldAlert = state.alerts[index];
        state.alerts[index] = { ...oldAlert, ...action.payload };
        
        // Update unread count
        if (oldAlert.status === 'active' && action.payload.status !== 'active') {
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        } else if (oldAlert.status !== 'active' && action.payload.status === 'active') {
          state.unreadCount += 1;
        }
      }
    },
    removeAlert: (state, action) => {
      const index = state.alerts.findIndex(alert => alert.id === action.payload);
      if (index !== -1) {
        const alert = state.alerts[index];
        if (alert.status === 'active') {
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
        state.alerts.splice(index, 1);
      }
    },
    setSelectedAlert: (state, action) => {
      state.selectedAlert = action.payload;
    },
    markAllAsRead: (state) => {
      state.alerts.forEach(alert => {
        if (alert.status === 'active') {
          alert.status = 'acknowledged';
        }
      });
      state.unreadCount = 0;
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setSortBy: (state, action) => {
      state.sortBy = action.payload;
    },
    setSortOrder: (state, action) => {
      state.sortOrder = action.payload;    },
    clearError: (state) => {
      state.error = null;
    },
    addPendingAck: (state, action) => {
      const alertId = action.payload;
      if (!state.pendingAcks.includes(alertId)) {
        state.pendingAcks.push(alertId);
      }
    },
    removePendingAck: (state, action) => {
      const alertId = action.payload;
      state.pendingAcks = state.pendingAcks.filter(id => id !== alertId);
    },
    clearPendingAcks: (state) => {
      state.pendingAcks = [];
    },
    resetAlertsState: () => initialState
  },
  extraReducers: (builder) => {
    builder
      // Fetch alerts
      .addCase(fetchAlerts.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAlerts.fulfilled, (state, action) => {
        state.loading = false;
        state.alerts = action.payload.alerts || action.payload;
        state.unreadCount = action.payload.unreadCount || 
          state.alerts.filter(alert => alert.status === 'active').length;
        state.lastUpdated = Date.now();
      })
      .addCase(fetchAlerts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })      // Acknowledge alert
      .addCase(acknowledgeAlert.fulfilled, (state, action) => {
        const index = state.alerts.findIndex(alert => alert.id === action.payload.alertId);
        if (index !== -1) {
          const oldStatus = state.alerts[index].status;
          state.alerts[index].status = 'acknowledged';
          state.alerts[index].acknowledgedAt = action.payload.acknowledgedAt;
          
          // Add visual indicator for offline acknowledgments
          if (action.payload.offline) {
            state.alerts[index].pendingSync = true;
            if (!state.pendingAcks.includes(action.payload.alertId)) {
              state.pendingAcks.push(action.payload.alertId);
            }
          } else {
            state.alerts[index].pendingSync = false;
            state.pendingAcks = state.pendingAcks.filter(id => id !== action.payload.alertId);
          }
          
          if (oldStatus === 'active') {
            state.unreadCount = Math.max(0, state.unreadCount - 1);
          }
        }
      })
      // Flush pending acknowledgments
      .addCase(flushPendingAcks.pending, (state) => {
        state.syncStatus = 'syncing';
      })
      .addCase(flushPendingAcks.fulfilled, (state, action) => {
        state.syncStatus = 'idle';
        
        // Update alerts that were successfully synced
        if (action.payload.results) {
          action.payload.results.forEach(result => {
            if (result.success) {
              const index = state.alerts.findIndex(alert => alert.id === result.alertId);
              if (index !== -1) {
                state.alerts[index].pendingSync = false;
              }
              state.pendingAcks = state.pendingAcks.filter(id => id !== result.alertId);
            }
          });
        }
      })
      .addCase(flushPendingAcks.rejected, (state, action) => {
        state.syncStatus = 'error';
        state.error = action.payload;
      })
      // Dismiss alert
      .addCase(dismissAlert.fulfilled, (state, action) => {
        const index = state.alerts.findIndex(alert => alert.id === action.payload.alertId);
        if (index !== -1) {
          const oldStatus = state.alerts[index].status;
          state.alerts[index].status = 'dismissed';
          state.alerts[index].dismissedAt = action.payload.dismissedAt;
          
          if (oldStatus === 'active') {
            state.unreadCount = Math.max(0, state.unreadCount - 1);
          }
        }
      })
      // Fetch alert details
      .addCase(fetchAlertDetails.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAlertDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedAlert = action.payload;
      })
      .addCase(fetchAlertDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const {
  addAlert,
  updateAlert,
  removeAlert,
  setSelectedAlert,
  markAllAsRead,
  setFilters,
  setSortBy,
  setSortOrder,
  clearError,
  addPendingAck,
  removePendingAck,
  clearPendingAcks,
  resetAlertsState
} = alertsSlice.actions;

// Selectors
export const selectAlerts = (state) => state.alerts.alerts;
export const selectSelectedAlert = (state) => state.alerts.selectedAlert;
export const selectUnreadCount = (state) => state.alerts.unreadCount;
export const selectAlertsLoading = (state) => state.alerts.loading;
export const selectAlertsError = (state) => state.alerts.error;
export const selectAlertFilters = (state) => state.alerts.filters;
export const selectAlertSortBy = (state) => state.alerts.sortBy;
export const selectAlertSortOrder = (state) => state.alerts.sortOrder;

export const selectFilteredAlerts = (state) => {
  const { alerts, filters, sortBy, sortOrder } = state.alerts;
  
  let filtered = alerts.filter(alert => {
    if (filters.status !== 'all' && alert.status !== filters.status) return false;
    if (filters.severity !== 'all' && alert.severity !== filters.severity) return false;
    if (filters.type !== 'all' && alert.type !== filters.type) return false;
    
    // Date range filtering
    if (filters.dateRange !== 'all') {
      const alertDate = new Date(alert.timestamp);
      const now = new Date();
      
      switch (filters.dateRange) {
        case 'today':
          if (alertDate.toDateString() !== now.toDateString()) return false;
          break;
        case 'week':
          const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          if (alertDate < weekAgo) return false;
          break;
        case 'month':
          const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          if (alertDate < monthAgo) return false;
          break;
      }
    }
    
    return true;
  });

  // Sort alerts
  filtered.sort((a, b) => {
    let comparison = 0;
    
    switch (sortBy) {
      case 'timestamp':
        comparison = new Date(a.timestamp) - new Date(b.timestamp);
        break;
      case 'severity':
        const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        comparison = (severityOrder[a.severity] || 0) - (severityOrder[b.severity] || 0);
        break;
      case 'type':
        comparison = a.type.localeCompare(b.type);
        break;
      default:
        comparison = 0;
    }
    
    return sortOrder === 'desc' ? -comparison : comparison;
  });

  return filtered;
};

export const selectActiveAlerts = (state) => {
  return state.alerts.alerts.filter(alert => alert.status === 'active');
};

export const selectCriticalAlerts = (state) => {
  return state.alerts.alerts.filter(alert => 
    alert.severity === 'critical' && alert.status === 'active'
  );
};

export default alertsSlice.reducer;
