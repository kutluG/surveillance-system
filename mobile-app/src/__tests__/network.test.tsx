import React from 'react';
import { render, waitFor, act } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import NetInfo from '@react-native-community/netinfo';
import secureStorage from '../utils/secureStorage';

import { NetworkProvider, useNetworkStatus } from '../contexts/NetworkProvider';
import networkReducer from '../store/slices/networkSlice';
import offlineApiService from '../services/offlineApiService';

// Mock dependencies
jest.mock('@react-native-community/netinfo');
jest.mock('../utils/secureStorage');

const mockNetInfo = NetInfo as jest.Mocked<typeof NetInfo>;
const mockSecureStorage = secureStorage as jest.Mocked<typeof secureStorage>;

// Test store setup
const createTestStore = () => configureStore({
  reducer: {
    network: networkReducer,
  },
});

// Test component to access network status
const TestComponent: React.FC = () => {
  const { isConnected, connectionType, refreshNetworkStatus } = useNetworkStatus();
  
  return (
    <>
      <div testID="connection-status">{isConnected ? 'online' : 'offline'}</div>
      <div testID="connection-type">{connectionType}</div>
      <button testID="refresh-button" onPress={refreshNetworkStatus}>
        Refresh
      </button>
    </>
  );
};

const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <NetworkProvider>
        {component}
      </NetworkProvider>
    </Provider>
  );
};

describe('NetworkProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSecureStorage.getItem.mockResolvedValue(null);
    mockSecureStorage.setItem.mockResolvedValue();
    mockSecureStorage.removeItem.mockResolvedValue();
  });

  describe('Network Status Detection', () => {
    it('should initialize with online status', async () => {
      const mockUnsubscribe = jest.fn();
      mockNetInfo.addEventListener.mockReturnValue(mockUnsubscribe);
      mockNetInfo.fetch.mockResolvedValue({
        isConnected: true,
        type: 'wifi',
      } as any);

      const { getByTestId } = renderWithProviders(<TestComponent />);
      
      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('online');
        expect(getByTestId('connection-type')).toHaveTextContent('wifi');
      });
    });

    it('should detect offline status', async () => {
      const mockUnsubscribe = jest.fn();
      let networkListener: (state: any) => void = () => {};
      
      mockNetInfo.addEventListener.mockImplementation((listener) => {
        networkListener = listener;
        return mockUnsubscribe;
      });

      const { getByTestId } = renderWithProviders(<TestComponent />);
      
      // Simulate going offline
      act(() => {
        networkListener({
          isConnected: false,
          type: 'none',
        });
      });

      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('offline');
        expect(getByTestId('connection-type')).toHaveTextContent('none');
      });
    });

    it('should handle network status changes', async () => {
      const mockUnsubscribe = jest.fn();
      let networkListener: (state: any) => void = () => {};
      
      mockNetInfo.addEventListener.mockImplementation((listener) => {
        networkListener = listener;
        return mockUnsubscribe;
      });

      const { getByTestId } = renderWithProviders(<TestComponent />);
      
      // Start online
      act(() => {
        networkListener({
          isConnected: true,
          type: 'wifi',
        });
      });

      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('online');
      });

      // Go offline
      act(() => {
        networkListener({
          isConnected: false,
          type: 'none',
        });
      });

      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('offline');
      });

      // Come back online with cellular
      act(() => {
        networkListener({
          isConnected: true,
          type: 'cellular',
        });
      });

      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('online');
        expect(getByTestId('connection-type')).toHaveTextContent('cellular');
      });
    });
  });

  describe('Caching and Persistence', () => {
    it('should cache network status to secure storage', async () => {
      const mockUnsubscribe = jest.fn();
      let networkListener: (state: any) => void = () => {};
      
      mockNetInfo.addEventListener.mockImplementation((listener) => {
        networkListener = listener;
        return mockUnsubscribe;
      });

      renderWithProviders(<TestComponent />);
      
      act(() => {
        networkListener({
          isConnected: false,
          type: 'none',
        });
      });

      await waitFor(() => {
        expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
          'networkStatus',
          expect.stringContaining('"isConnected":false')
        );
      });
    });

    it('should load cached network status on initialization', async () => {
      mockSecureStorage.getItem.mockResolvedValue(
        JSON.stringify({
          isConnected: false,
          timestamp: new Date().toISOString(),
        })
      );

      const mockUnsubscribe = jest.fn();
      mockNetInfo.addEventListener.mockReturnValue(mockUnsubscribe);

      const { getByTestId } = renderWithProviders(<TestComponent />);
      
      await waitFor(() => {
        expect(mockSecureStorage.getItem).toHaveBeenCalledWith('networkStatus');
      });
    });
  });

  describe('Offline Data Sync', () => {
    it('should trigger sync when coming back online', async () => {
      const mockOfflineData = JSON.stringify([
        { action: 'test', timestamp: new Date().toISOString() }
      ]);
      
      mockSecureStorage.getItem
        .mockResolvedValueOnce(null) // networkStatus
        .mockResolvedValueOnce(mockOfflineData); // offlineData

      const mockUnsubscribe = jest.fn();
      let networkListener: (state: any) => void = () => {};
      
      mockNetInfo.addEventListener.mockImplementation((listener) => {
        networkListener = listener;
        return mockUnsubscribe;
      });

      renderWithProviders(<TestComponent />);
      
      // Start offline
      act(() => {
        networkListener({
          isConnected: false,
          type: 'none',
        });
      });

      // Come back online
      act(() => {
        networkListener({
          isConnected: true,
          type: 'wifi',
        });
      });

      await waitFor(() => {
        expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('offlineData');
      });
    });
  });
});

describe('OfflineApiService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSecureStorage.getItem.mockResolvedValue(null);
    mockSecureStorage.setItem.mockResolvedValue();
    mockSecureStorage.getAllKeys.mockResolvedValue([]);
    mockSecureStorage.removeItem.mockResolvedValue();
  });

  describe('Caching', () => {
    it('should cache API responses', async () => {
      const mockResponse = { data: 'test' };
      const mockApiCall = jest.fn().mockResolvedValue(mockResponse);
      
      mockNetInfo.fetch.mockResolvedValue({ isConnected: true } as any);

      const result = await offlineApiService.makeRequest(mockApiCall, {
        cacheKey: 'test_key',
        cacheDuration: 5000,
      });

      expect(result).toBe(mockResponse);
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
        'api_cache_test_key',
        expect.stringContaining('"data":"test"')
      );
    });

    it('should return cached data when available', async () => {
      const cachedData = {
        data: { cached: 'response' },
        timestamp: new Date().toISOString(),
        expiry: new Date(Date.now() + 10000).toISOString(),
      };
      
      mockSecureStorage.getItem.mockResolvedValue(JSON.stringify(cachedData));
      mockNetInfo.fetch.mockResolvedValue({ isConnected: true } as any);

      const mockApiCall = jest.fn();
      
      const result = await offlineApiService.makeRequest(mockApiCall, {
        cacheKey: 'test_key',
      });

      expect(result).toEqual(cachedData.data);
      expect(mockApiCall).not.toHaveBeenCalled();
    });

    it('should ignore expired cache', async () => {
      const expiredData = {
        data: { expired: 'data' },
        timestamp: new Date().toISOString(),
        expiry: new Date(Date.now() - 1000).toISOString(), // Expired
      };
      
      mockSecureStorage.getItem.mockResolvedValue(JSON.stringify(expiredData));
      mockNetInfo.fetch.mockResolvedValue({ isConnected: true } as any);

      const freshResponse = { fresh: 'data' };
      const mockApiCall = jest.fn().mockResolvedValue(freshResponse);
      
      const result = await offlineApiService.makeRequest(mockApiCall, {
        cacheKey: 'test_key',
      });

      expect(result).toBe(freshResponse);
      expect(mockApiCall).toHaveBeenCalled();
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('api_cache_test_key');
    });
  });

  describe('Offline Queue', () => {
    it('should queue requests when offline', async () => {
      mockNetInfo.fetch.mockResolvedValue({ isConnected: false } as any);
      
      const mockApiCall = jest.fn();
      
      await expect(
        offlineApiService.makeRequest(mockApiCall, {
          offlineSupport: true,
          retryOnReconnect: true,
        })
      ).rejects.toThrow('Device is offline');      expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
        'offline_queue',
        expect.stringContaining('"timestamp"')
      );
    });

    it('should reject offline requests without offline support', async () => {
      mockNetInfo.fetch.mockResolvedValue({ isConnected: false } as any);
      
      const mockApiCall = jest.fn();
      
      await expect(
        offlineApiService.makeRequest(mockApiCall, {
          offlineSupport: false,
        })
      ).rejects.toThrow('Device is offline and request does not support offline mode');
    });
  });

  describe('Cache Management', () => {
    it('should clear cache by pattern', async () => {
      const mockKeys = [
        'api_cache_cameras_list',
        'api_cache_cameras_details',
        'api_cache_alerts_list',
        'other_key',
      ];
      
      mockSecureStorage.getAllKeys.mockResolvedValue(mockKeys);
        await offlineApiService.clearCache('cameras');
      
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('api_cache_cameras_list');
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('api_cache_cameras_details');
      expect(mockSecureStorage.removeItem).toHaveBeenCalledTimes(2);
    });

    it('should clear all cache when no pattern provided', async () => {
      const mockKeys = [
        'api_cache_cameras_list',
        'api_cache_alerts_list',
        'other_key',
      ];
        mockSecureStorage.getAllKeys.mockResolvedValue(mockKeys);
      
      await offlineApiService.clearCache();
      
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('api_cache_cameras_list');
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('api_cache_alerts_list');
      expect(mockSecureStorage.removeItem).toHaveBeenCalledTimes(2);
    });
  });

  describe('Enhanced Service Methods', () => {
    it('should call getCameras with proper caching', async () => {
      mockNetInfo.fetch.mockResolvedValue({ isConnected: true } as any);
      
      const mockCameras = [{ id: 1, name: 'Camera 1' }];
        // Mock the dynamic import
      jest.doMock('../services/cameraService', () => ({
        cameraService: {
          getCameras: jest.fn().mockResolvedValue(mockCameras),
        },
      }));

      const result = await offlineApiService.getCameras({ location: 'office' });
      
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
        expect.stringContaining('api_cache_cameras_'),
        expect.any(String)
      );
    });
  });
});

describe('Integration Tests', () => {
  it('should handle complete offline-to-online flow', async () => {
    const mockUnsubscribe = jest.fn();
    let networkListener: (state: any) => void = () => {};
    
    mockNetInfo.addEventListener.mockImplementation((listener) => {
      networkListener = listener;
      return mockUnsubscribe;
    });

    const { getByTestId } = renderWithProviders(<TestComponent />);
    
    // Start online
    act(() => {
      networkListener({
        isConnected: true,
        type: 'wifi',
      });
    });

    await waitFor(() => {
      expect(getByTestId('connection-status')).toHaveTextContent('online');
    });

    // Go offline
    act(() => {
      networkListener({
        isConnected: false,
        type: 'none',
      });
    });

    await waitFor(() => {
      expect(getByTestId('connection-status')).toHaveTextContent('offline');
    });

    // Come back online
    act(() => {
      networkListener({
        isConnected: true,
        type: 'cellular',
      });
    });

    await waitFor(() => {
      expect(getByTestId('connection-status')).toHaveTextContent('online');
      expect(getByTestId('connection-type')).toHaveTextContent('cellular');
    });
  });
});
