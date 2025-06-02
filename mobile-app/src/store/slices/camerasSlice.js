import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { cameraService } from '../../services/cameraService';

// Async thunks
export const fetchCameras = createAsyncThunk(
  'cameras/fetchCameras',
  async (_, { rejectWithValue }) => {
    try {
      const response = await cameraService.getCameras();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchCameraDetails = createAsyncThunk(
  'cameras/fetchCameraDetails',
  async (cameraId, { rejectWithValue }) => {
    try {
      const response = await cameraService.getCameraDetails(cameraId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateCameraSettings = createAsyncThunk(
  'cameras/updateCameraSettings',
  async ({ cameraId, settings }, { rejectWithValue }) => {
    try {
      const response = await cameraService.updateCameraSettings(cameraId, settings);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const toggleCameraRecording = createAsyncThunk(
  'cameras/toggleCameraRecording',
  async ({ cameraId, recording }, { rejectWithValue }) => {
    try {
      const response = await cameraService.toggleRecording(cameraId, recording);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  cameras: [],
  selectedCamera: null,
  cameraFeeds: {},
  loading: false,
  error: null,
  lastUpdated: null,
  filters: {
    status: 'all', // all, online, offline, recording
    location: 'all',
    type: 'all'
  },
  sortBy: 'name' // name, status, location, lastActivity
};

const camerasSlice = createSlice({
  name: 'cameras',
  initialState,
  reducers: {
    setCameras: (state, action) => {
      state.cameras = action.payload;
      state.lastUpdated = Date.now();
    },
    updateCamera: (state, action) => {
      const index = state.cameras.findIndex(cam => cam.id === action.payload.id);
      if (index !== -1) {
        state.cameras[index] = { ...state.cameras[index], ...action.payload };
      }
    },
    setSelectedCamera: (state, action) => {
      state.selectedCamera = action.payload;
    },
    updateCameraFeed: (state, action) => {
      const { cameraId, feedData } = action.payload;
      state.cameraFeeds[cameraId] = feedData;
    },
    removeCameraFeed: (state, action) => {
      delete state.cameraFeeds[action.payload];
    },
    updateCameraStatus: (state, action) => {
      const { cameraId, status } = action.payload;
      const camera = state.cameras.find(cam => cam.id === cameraId);
      if (camera) {
        camera.status = status;
        camera.lastActivity = Date.now();
      }
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setSortBy: (state, action) => {
      state.sortBy = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    resetCamerasState: () => initialState
  },
  extraReducers: (builder) => {
    builder
      // Fetch cameras
      .addCase(fetchCameras.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCameras.fulfilled, (state, action) => {
        state.loading = false;
        state.cameras = action.payload;
        state.lastUpdated = Date.now();
      })
      .addCase(fetchCameras.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Fetch camera details
      .addCase(fetchCameraDetails.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCameraDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedCamera = action.payload;
      })
      .addCase(fetchCameraDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Update camera settings
      .addCase(updateCameraSettings.fulfilled, (state, action) => {
        const index = state.cameras.findIndex(cam => cam.id === action.payload.id);
        if (index !== -1) {
          state.cameras[index] = { ...state.cameras[index], ...action.payload };
        }
        if (state.selectedCamera?.id === action.payload.id) {
          state.selectedCamera = { ...state.selectedCamera, ...action.payload };
        }
      })
      // Toggle recording
      .addCase(toggleCameraRecording.fulfilled, (state, action) => {
        const index = state.cameras.findIndex(cam => cam.id === action.payload.id);
        if (index !== -1) {
          state.cameras[index].recording = action.payload.recording;
        }
        if (state.selectedCamera?.id === action.payload.id) {
          state.selectedCamera.recording = action.payload.recording;
        }
      });
  }
});

export const {
  setCameras,
  updateCamera,
  setSelectedCamera,
  updateCameraFeed,
  removeCameraFeed,
  updateCameraStatus,
  setFilters,
  setSortBy,
  clearError,
  resetCamerasState
} = camerasSlice.actions;

// Selectors
export const selectCameras = (state) => state.cameras.cameras;
export const selectSelectedCamera = (state) => state.cameras.selectedCamera;
export const selectCameraFeeds = (state) => state.cameras.cameraFeeds;
export const selectCamerasLoading = (state) => state.cameras.loading;
export const selectCamerasError = (state) => state.cameras.error;
export const selectCameraFilters = (state) => state.cameras.filters;
export const selectCameraSortBy = (state) => state.cameras.sortBy;

export const selectFilteredCameras = (state) => {
  const { cameras, filters, sortBy } = state.cameras;
  
  let filtered = cameras.filter(camera => {
    if (filters.status !== 'all' && camera.status !== filters.status) return false;
    if (filters.location !== 'all' && camera.location !== filters.location) return false;
    if (filters.type !== 'all' && camera.type !== filters.type) return false;
    return true;
  });

  // Sort cameras
  filtered.sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name);
      case 'status':
        return a.status.localeCompare(b.status);
      case 'location':
        return a.location.localeCompare(b.location);
      case 'lastActivity':
        return new Date(b.lastActivity) - new Date(a.lastActivity);
      default:
        return 0;
    }
  });

  return filtered;
};

export default camerasSlice.reducer;
