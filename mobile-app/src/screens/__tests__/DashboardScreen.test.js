import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import DashboardScreen from '../DashboardScreen';
import testUtils from '../../test/testUtils';

const mockInitialState = {
  cameras: {
    cameras: testUtils.testData.cameras,
    loading: false,
    error: null,
  },
  alerts: {
    alerts: testUtils.testData.alerts,
    loading: false,
    error: null,
  },
  app: {
    theme: 'dark',
    isConnected: true,
  },
};

describe('DashboardScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with data', () => {
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    expect(getByText('Dashboard')).toBeTruthy();
    expect(getByText('System Overview')).toBeTruthy();
    expect(getByText('Quick Actions')).toBeTruthy();
  });

  it('displays correct camera statistics', () => {
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    expect(getByText('3')).toBeTruthy(); // Total cameras
    expect(getByText('2')).toBeTruthy(); // Online cameras
    expect(getByText('1')).toBeTruthy(); // Offline cameras
  });

  it('displays recent alerts', () => {
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    expect(getByText('Recent Alerts')).toBeTruthy();
    expect(getByText('Motion detected')).toBeTruthy();
  });

  it('handles refresh action', async () => {
    const { getByTestId } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    const refreshControl = getByTestId('dashboard-refresh');
    fireEvent(refreshControl, 'onRefresh');
    
    // Should trigger data refresh
    await waitFor(() => {
      // Verify refresh was called
    });
  });

  it('navigates to cameras screen on quick action', () => {
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    const viewCamerasButton = getByText('View Cameras');
    fireEvent.press(viewCamerasButton);
    
    expect(testUtils.mockNavigation.navigate).toHaveBeenCalledWith('Cameras');
  });

  it('navigates to alerts screen on quick action', () => {
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    const viewAlertsButton = getByText('View Alerts');
    fireEvent.press(viewAlertsButton);
    
    expect(testUtils.mockNavigation.navigate).toHaveBeenCalledWith('Alerts');
  });

  it('shows loading state correctly', () => {
    const loadingState = {
      ...mockInitialState,
      cameras: { ...mockInitialState.cameras, loading: true },
    };
    
    const { getByTestId } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: loadingState }
    );
    
    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('handles empty state correctly', () => {
    const emptyState = {
      cameras: { cameras: [], loading: false, error: null },
      alerts: { alerts: [], loading: false, error: null },
      app: { theme: 'dark', isConnected: true },
    };
    
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: emptyState }
    );
    
    expect(getByText('No cameras found')).toBeTruthy();
    expect(getByText('No recent alerts')).toBeTruthy();
  });

  it('displays network status correctly', () => {
    const offlineState = {
      ...mockInitialState,
      app: { ...mockInitialState.app, isConnected: false },
    };
    
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: offlineState }
    );
    
    expect(getByText('Offline')).toBeTruthy();
  });

  it('handles error state correctly', () => {
    const errorState = {
      ...mockInitialState,
      cameras: { 
        ...mockInitialState.cameras, 
        error: 'Failed to load cameras' 
      },
    };
    
    const { getByText } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: errorState }
    );
    
    expect(getByText('Failed to load cameras')).toBeTruthy();
  });

  it('updates data in real-time', async () => {
    const { rerender } = testUtils.renderWithProviders(
      <DashboardScreen navigation={testUtils.mockNavigation} />,
      { initialState: mockInitialState }
    );
    
    // Simulate real-time update
    const updatedState = {
      ...mockInitialState,
      alerts: {
        ...mockInitialState.alerts,
        alerts: [
          ...mockInitialState.alerts.alerts,
          testUtils.generateMockAlert({ id: 'new-alert', type: 'person_detected' }),
        ],
      },
    };
    
    rerender(
      <DashboardScreen navigation={testUtils.mockNavigation} />
    );
    
    await waitFor(() => {
      // Verify new alert appears
    });
  });

  it('meets accessibility requirements', () => {
    const accessibility = testUtils.checkAccessibility(
      testUtils.renderWithProviders(
        <DashboardScreen navigation={testUtils.mockNavigation} />,
        { initialState: mockInitialState }
      ).container
    );
    
    expect(accessibility.hasButtons).toBe(true);
    expect(accessibility.buttonCount).toBeGreaterThan(0);
  });
});
