import { configureStore } from '@reduxjs/toolkit';
import { 
  acknowledgeAlert, 
  flushPendingAcks,
  addPendingAck,
  removePendingAck 
} from './alertsSlice';
import { setNetworkStatus } from './networkSlice';
import alertsReducer from './alertsSlice';
import networkReducer from './networkSlice';
import secureStorage from '../../utils/secureStorage';
import { alertService } from '../../services/alertService';

// Mock dependencies
jest.mock('../../utils/secureStorage');
jest.mock('../../services/alertService');

const mockSecureStorage = secureStorage as jest.Mocked<typeof secureStorage>;
const mockAlertService = alertService as jest.Mocked<typeof alertService>;

describe('Alert Actions - Offline Acknowledgment', () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        alerts: alertsReducer,
        network: networkReducer,
      },
    });

    // Reset mocks
    jest.clearAllMocks();
    mockSecureStorage.getItem.mockResolvedValue(null);
    mockSecureStorage.setItem.mockResolvedValue(undefined);
  });

  describe('acknowledgeAlert', () => {
    const alertId = 'test-alert-123';
    const mockAlert = {
      id: alertId,
      message: 'Motion detected',
      status: 'new',
      timestamp: '2025-06-08T10:00:00Z'
    };

    beforeEach(() => {
      // Add test alert to store
      store.dispatch({
        type: 'alerts/addAlert',
        payload: mockAlert
      });
    });

    it('should acknowledge alert online successfully', async () => {
      // Setup online state
      store.dispatch(setNetworkStatus({ isConnected: true }));
      
      // Mock successful API response
      mockAlertService.acknowledgeAlert.mockResolvedValue({
        data: { acknowledgedAt: '2025-06-08T10:01:00Z' }
      });

      // Dispatch acknowledge action
      const result = await store.dispatch(acknowledgeAlert(alertId));

      // Verify API was called
      expect(mockAlertService.acknowledgeAlert).toHaveBeenCalledWith(alertId);

      // Verify alert was updated in store
      const state = store.getState();
      const updatedAlert = state.alerts.alerts.find(a => a.id === alertId);
      expect(updatedAlert?.status).toBe('acknowledged');
      expect(updatedAlert?.pendingSync).toBe(false);
      expect(result.meta.requestStatus).toBe('fulfilled');
    });

    it('should store acknowledgment for offline sync when offline', async () => {
      // Setup offline state
      store.dispatch(setNetworkStatus({ isConnected: false }));

      // Mock empty pending queue
      mockSecureStorage.getItem.mockResolvedValue(null);

      // Dispatch acknowledge action
      const result = await store.dispatch(acknowledgeAlert(alertId));

      // Verify API was not called
      expect(mockAlertService.acknowledgeAlert).not.toHaveBeenCalled();

      // Verify pending acknowledgment was stored
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
        'pendingAcks',
        expect.stringContaining(alertId)
      );

      // Verify alert was optimistically updated
      const state = store.getState();
      const updatedAlert = state.alerts.alerts.find(a => a.id === alertId);
      expect(updatedAlert?.status).toBe('acknowledged');
      expect(updatedAlert?.pendingSync).toBe(true);
      expect(state.alerts.pendingAcks).toContain(alertId);
      expect(result.meta.requestStatus).toBe('fulfilled');
    });

    it('should fall back to offline mode on API failure', async () => {
      // Setup online state
      store.dispatch(setNetworkStatus({ isConnected: true }));

      // Mock API failure
      mockAlertService.acknowledgeAlert.mockRejectedValue(
        new Error('Network error')
      );

      // Dispatch acknowledge action
      const result = await store.dispatch(acknowledgeAlert(alertId));

      // Verify API was called
      expect(mockAlertService.acknowledgeAlert).toHaveBeenCalledWith(alertId);

      // Verify fallback to offline mode
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith(
        'pendingAcks',
        expect.stringContaining(alertId)
      );

      // Verify optimistic update
      const state = store.getState();
      const updatedAlert = state.alerts.alerts.find(a => a.id === alertId);
      expect(updatedAlert?.status).toBe('acknowledged');
      expect(updatedAlert?.pendingSync).toBe(true);
      expect(result.meta.requestStatus).toBe('fulfilled');
    });

    it('should not create duplicate pending acknowledgments', async () => {
      // Setup offline state
      store.dispatch(setNetworkStatus({ isConnected: false }));

      // Mock existing pending acknowledgment
      const existingPending = JSON.stringify([
        { alertId, timestamp: '2025-06-08T09:00:00Z', retryCount: 0 }
      ]);
      mockSecureStorage.getItem.mockResolvedValue(existingPending);

      // Dispatch acknowledge action
      await store.dispatch(acknowledgeAlert(alertId));

      // Verify setItem was called only once (to read, not to add duplicate)
      const setItemCalls = mockSecureStorage.setItem.mock.calls.filter(
        call => call[0] === 'pendingAcks'
      );
      expect(setItemCalls).toHaveLength(0); // Should not add duplicate
    });
  });

  describe('flushPendingAcks', () => {
    it('should process pending acknowledgments successfully', async () => {
      const alertId1 = 'alert-1';
      const alertId2 = 'alert-2';
      
      // Mock pending acknowledgments
      const pendingAcks = JSON.stringify([
        { alertId: alertId1, timestamp: '2025-06-08T09:00:00Z', retryCount: 0 },
        { alertId: alertId2, timestamp: '2025-06-08T09:01:00Z', retryCount: 0 }
      ]);
      mockSecureStorage.getItem.mockResolvedValue(pendingAcks);

      // Mock successful API responses
      mockAlertService.acknowledgeAlert
        .mockResolvedValueOnce({ data: { acknowledgedAt: '2025-06-08T10:00:00Z' } })
        .mockResolvedValueOnce({ data: { acknowledgedAt: '2025-06-08T10:01:00Z' } });

      // Dispatch flush action
      const result = await store.dispatch(flushPendingAcks());

      // Verify API calls
      expect(mockAlertService.acknowledgeAlert).toHaveBeenCalledTimes(2);
      expect(mockAlertService.acknowledgeAlert).toHaveBeenCalledWith(alertId1);
      expect(mockAlertService.acknowledgeAlert).toHaveBeenCalledWith(alertId2);

      // Verify empty queue was stored (all processed)
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith('pendingAcks', '[]');

      // Verify result
      expect(result.payload).toEqual({
        processed: 2,
        failed: 0,
        results: expect.arrayContaining([
          expect.objectContaining({ alertId: alertId1, success: true }),
          expect.objectContaining({ alertId: alertId2, success: true })
        ])
      });
    });

    it('should handle API failures and retry logic', async () => {
      const alertId = 'alert-1';
      
      // Mock pending acknowledgment with existing retry count
      const pendingAcks = JSON.stringify([
        { alertId, timestamp: '2025-06-08T09:00:00Z', retryCount: 1 }
      ]);
      mockSecureStorage.getItem.mockResolvedValue(pendingAcks);

      // Mock API failure
      mockAlertService.acknowledgeAlert.mockRejectedValue(
        new Error('API Error')
      );

      // Dispatch flush action
      const result = await store.dispatch(flushPendingAcks());

      // Verify failed result
      expect(result.payload).toEqual({
        processed: 0,
        failed: 1,
        results: expect.arrayContaining([
          expect.objectContaining({ 
            alertId, 
            success: false,
            retryCount: 2 
          })
        ])
      });

      // Verify failed acknowledgment remains in queue with incremented retry count
      const updatedQueue = JSON.parse(mockSecureStorage.setItem.mock.calls[0][1]);
      expect(updatedQueue[0].retryCount).toBe(2);
    });

    it('should skip acknowledgments that exceed max retries', async () => {
      const alertId = 'alert-1';
      
      // Mock pending acknowledgment with max retries
      const pendingAcks = JSON.stringify([
        { alertId, timestamp: '2025-06-08T09:00:00Z', retryCount: 3 }
      ]);
      mockSecureStorage.getItem.mockResolvedValue(pendingAcks);

      // Dispatch flush action
      const result = await store.dispatch(flushPendingAcks());

      // Verify API was not called for max retry item
      expect(mockAlertService.acknowledgeAlert).not.toHaveBeenCalled();

      // Verify result shows no processing
      expect(result.payload).toEqual({
        processed: 0,
        failed: 0,
        results: []
      });
    });

    it('should handle empty pending queue', async () => {
      // Mock empty queue
      mockSecureStorage.getItem.mockResolvedValue(null);

      // Dispatch flush action
      const result = await store.dispatch(flushPendingAcks());

      // Verify no API calls
      expect(mockAlertService.acknowledgeAlert).not.toHaveBeenCalled();

      // Verify result
      expect(result.payload).toEqual({ processed: 0 });
    });
  });

  describe('pending acknowledgment reducers', () => {
    it('should add pending acknowledgment', () => {
      const alertId = 'test-alert';
      
      store.dispatch(addPendingAck(alertId));
      
      const state = store.getState();
      expect(state.alerts.pendingAcks).toContain(alertId);
    });

    it('should remove pending acknowledgment', () => {
      const alertId = 'test-alert';
      
      // Add then remove
      store.dispatch(addPendingAck(alertId));
      store.dispatch(removePendingAck(alertId));
      
      const state = store.getState();
      expect(state.alerts.pendingAcks).not.toContain(alertId);
    });

    it('should not add duplicate pending acknowledgments', () => {
      const alertId = 'test-alert';
      
      // Add twice
      store.dispatch(addPendingAck(alertId));
      store.dispatch(addPendingAck(alertId));
      
      const state = store.getState();
      const count = state.alerts.pendingAcks.filter(id => id === alertId).length;
      expect(count).toBe(1);
    });
  });
});
