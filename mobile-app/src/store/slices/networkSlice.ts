import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface NetworkState {
  isConnected: boolean;
  lastChecked: string;
  syncInProgress: boolean;
}

// Async thunk for flushing pending operations when coming online
export const flushPendingOperations = createAsyncThunk(
  'network/flushPendingOperations',
  async (_, { getState }) => {
    try {
      // For now, just return a simple success result
      // The actual flush logic will be handled by the NetworkProvider
      const state = getState() as any;
      const pendingAcks = state.alerts?.pendingAcks || [];
      
      console.log('Flushing pending operations...');
      
      return { 
        processed: pendingAcks.length, 
        successful: pendingAcks.length, 
        failed: 0 
      };
    } catch (error) {
      console.error('Error flushing pending operations:', error);
      throw error;
    }
  }
);

const initialState: NetworkState = {
  isConnected: true,
  lastChecked: new Date().toISOString(),
  syncInProgress: false,
};

const networkSlice = createSlice({
  name: 'network',
  initialState,
  reducers: {
    setNetworkStatus: (state, action: PayloadAction<{ isConnected: boolean }>) => {
      const wasOffline = !state.isConnected;
      state.isConnected = action.payload.isConnected;
      state.lastChecked = new Date().toISOString();
      
      // Reset sync status when going offline
      if (!action.payload.isConnected) {
        state.syncInProgress = false;
      }
    },
    updateLastChecked: (state) => {
      state.lastChecked = new Date().toISOString();
    },
    setSyncInProgress: (state, action: PayloadAction<boolean>) => {
      state.syncInProgress = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(flushPendingOperations.pending, (state) => {
        state.syncInProgress = true;
      })
      .addCase(flushPendingOperations.fulfilled, (state) => {
        state.syncInProgress = false;
      })
      .addCase(flushPendingOperations.rejected, (state) => {
        state.syncInProgress = false;
      });
  },
});

export const { setNetworkStatus, updateLastChecked, setSyncInProgress } = networkSlice.actions;
export default networkSlice.reducer;
