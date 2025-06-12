import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import NetInfo from '@react-native-community/netinfo';
import { useDispatch, useSelector } from 'react-redux';
import secureStorage from '../utils/secureStorage';
import { setNetworkStatus, flushPendingOperations } from '../store/slices/networkSlice';
import { RootState } from '../store';

interface NetworkContextType {
  isConnected: boolean;
  lastChecked: string;
  connectionType: string;
  syncInProgress: boolean;
  refreshNetworkStatus: () => Promise<void>;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

export const useNetworkStatus = (): NetworkContextType => {
  const context = useContext(NetworkContext);
  if (!context) {
    throw new Error('useNetworkStatus must be used within a NetworkProvider');
  }
  return context;
};

interface NetworkProviderProps {
  children: ReactNode;
}

const NETWORK_STATUS_KEY = 'networkStatus';
const OFFLINE_DATA_KEY = 'offlineData';

export const NetworkProvider: React.FC<NetworkProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const { isConnected, lastChecked, syncInProgress } = useSelector((state: RootState) => state.network);
  const [connectionType, setConnectionType] = React.useState<string>('unknown');

  // Load cached network status on app start
  useEffect(() => {
    loadCachedNetworkStatus();
  }, []);

  // Set up network listener
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      const connected = Boolean(state.isConnected);
      const wasOffline = !isConnected;
      
      setConnectionType(state.type || 'unknown');
      
      // Update Redux store
      dispatch(setNetworkStatus({ isConnected: connected }));
      
      // Cache network status
      cacheNetworkStatus(connected);
        // Handle offline data sync when coming online
      if (connected && wasOffline && !syncInProgress) {
        console.log('Device came back online, flushing pending operations...');
        dispatch(flushPendingOperations() as any);
      }
    });

    return unsubscribe;
  }, [dispatch, isConnected, syncInProgress]);
  const loadCachedNetworkStatus = async () => {
    try {
      const cachedStatus = await secureStorage.getItem(NETWORK_STATUS_KEY);
      if (cachedStatus) {
        const { isConnected: cachedConnected } = JSON.parse(cachedStatus);
        dispatch(setNetworkStatus({ isConnected: cachedConnected }));
      }
    } catch (error) {
      console.error('Error loading cached network status:', error);
    }
  };
  const cacheNetworkStatus = async (connected: boolean) => {
    try {
      const statusData = {
        isConnected: connected,
        timestamp: new Date().toISOString(),
      };
      await secureStorage.setItem(NETWORK_STATUS_KEY, JSON.stringify(statusData));
    } catch (error) {
      console.error('Error caching network status:', error);
    }
  };
  const syncOfflineData = async () => {
    try {
      const offlineData = await secureStorage.getItem(OFFLINE_DATA_KEY);
      if (offlineData) {
        const data = JSON.parse(offlineData);
        console.log('Syncing offline data:', data);
        // TODO: Implement actual sync logic here
        // This would typically involve sending queued API calls
        await secureStorage.removeItem(OFFLINE_DATA_KEY);
      }
    } catch (error) {
      console.error('Error syncing offline data:', error);
    }
  };

  const refreshNetworkStatus = async (): Promise<void> => {
    try {
      const state = await NetInfo.fetch();
      const connected = Boolean(state.isConnected);
      setConnectionType(state.type || 'unknown');
      dispatch(setNetworkStatus({ isConnected: connected }));
      await cacheNetworkStatus(connected);
    } catch (error) {
      console.error('Error refreshing network status:', error);
    }
  };
  const contextValue: NetworkContextType = {
    isConnected,
    lastChecked,
    connectionType,
    syncInProgress,
    refreshNetworkStatus,
  };

  return (
    <NetworkContext.Provider value={contextValue}>
      {children}
    </NetworkContext.Provider>
  );
};

// Utility function to store data for offline sync
export const storeOfflineData = async (data: any): Promise<void> => {
  try {
    const existingData = await secureStorage.getItem(OFFLINE_DATA_KEY);
    const offlineQueue = existingData ? JSON.parse(existingData) : [];
    offlineQueue.push({
      ...data,
      timestamp: new Date().toISOString(),
    });
    await secureStorage.setItem(OFFLINE_DATA_KEY, JSON.stringify(offlineQueue));
  } catch (error) {
    console.error('Error storing offline data:', error);
  }
};

// Utility function to check if device is online
export const isOnline = (): Promise<boolean> => {
  return NetInfo.fetch().then(state => Boolean(state.isConnected));
};
