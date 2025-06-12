import { configureStore } from '@reduxjs/toolkit';
import camerasReducer from './slices/camerasSlice';
import alertsReducer from './slices/alertsSlice';
import appReducer from './slices/appSlice';
import networkReducer from './slices/networkSlice';

export const store = configureStore({
  reducer: {
    cameras: camerasReducer,
    alerts: alertsReducer,
    app: appReducer,
    network: networkReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
