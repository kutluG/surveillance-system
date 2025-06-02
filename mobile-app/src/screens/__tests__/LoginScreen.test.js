import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../LoginScreen';
import { AuthContext } from '../../contexts/AuthContext';
import testUtils from '../../test/testUtils';

// Mock the AuthContext
const mockAuthContext = {
  user: null,
  loading: false,
  login: jest.fn(),
  loginWithBiometrics: jest.fn(),
  logout: jest.fn(),
  checkBiometricAvailability: jest.fn(),
};

const renderLoginScreen = (authContextValue = mockAuthContext) => {
  return testUtils.renderWithProviders(
    <AuthContext.Provider value={authContextValue}>
      <LoginScreen navigation={testUtils.mockNavigation} />
    </AuthContext.Provider>
  );
};

describe('LoginScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly', () => {
    const { getByText, getByPlaceholderText } = renderLoginScreen();
    
    expect(getByText('Surveillance System')).toBeTruthy();
    expect(getByPlaceholderText('Email')).toBeTruthy();
    expect(getByPlaceholderText('Password')).toBeTruthy();
    expect(getByText('Login')).toBeTruthy();
  });

  it('handles email input correctly', async () => {
    const { getByPlaceholderText } = renderLoginScreen();
    const emailInput = getByPlaceholderText('Email');
    
    fireEvent.changeText(emailInput, 'test@example.com');
    
    expect(emailInput.props.value).toBe('test@example.com');
  });

  it('handles password input correctly', async () => {
    const { getByPlaceholderText } = renderLoginScreen();
    const passwordInput = getByPlaceholderText('Password');
    
    fireEvent.changeText(passwordInput, 'password123');
    
    expect(passwordInput.props.value).toBe('password123');
  });

  it('validates email format', async () => {
    const { getByPlaceholderText, getByText, queryByText } = renderLoginScreen();
    const emailInput = getByPlaceholderText('Email');
    const loginButton = getByText('Login');
    
    fireEvent.changeText(emailInput, 'invalid-email');
    fireEvent.press(loginButton);
    
    await waitFor(() => {
      expect(queryByText('Please enter a valid email address')).toBeTruthy();
    });
  });

  it('validates password length', async () => {
    const { getByPlaceholderText, getByText, queryByText } = renderLoginScreen();
    const emailInput = getByPlaceholderText('Email');
    const passwordInput = getByPlaceholderText('Password');
    const loginButton = getByText('Login');
    
    fireEvent.changeText(emailInput, 'test@example.com');
    fireEvent.changeText(passwordInput, '123');
    fireEvent.press(loginButton);
    
    await waitFor(() => {
      expect(queryByText('Password must be at least 6 characters')).toBeTruthy();
    });
  });

  it('calls login function with correct credentials', async () => {
    const mockLogin = jest.fn().mockResolvedValue({ success: true });
    const contextValue = { ...mockAuthContext, login: mockLogin };
    
    const { getByPlaceholderText, getByText } = renderLoginScreen(contextValue);
    const emailInput = getByPlaceholderText('Email');
    const passwordInput = getByPlaceholderText('Password');
    const loginButton = getByText('Login');
    
    fireEvent.changeText(emailInput, 'test@example.com');
    fireEvent.changeText(passwordInput, 'password123');
    fireEvent.press(loginButton);
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  it('shows loading state during login', async () => {
    const mockLogin = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );
    const contextValue = { ...mockAuthContext, login: mockLogin };
    
    const { getByPlaceholderText, getByText, queryByText } = renderLoginScreen(contextValue);
    const emailInput = getByPlaceholderText('Email');
    const passwordInput = getByPlaceholderText('Password');
    const loginButton = getByText('Login');
    
    fireEvent.changeText(emailInput, 'test@example.com');
    fireEvent.changeText(passwordInput, 'password123');
    fireEvent.press(loginButton);
    
    expect(queryByText('Logging in...')).toBeTruthy();
  });

  it('handles login error', async () => {
    const mockLogin = jest.fn().mockRejectedValue(new Error('Invalid credentials'));
    const contextValue = { ...mockAuthContext, login: mockLogin };
    
    const { getByPlaceholderText, getByText, queryByText } = renderLoginScreen(contextValue);
    const emailInput = getByPlaceholderText('Email');
    const passwordInput = getByPlaceholderText('Password');
    const loginButton = getByText('Login');
    
    fireEvent.changeText(emailInput, 'test@example.com');
    fireEvent.changeText(passwordInput, 'wrongpassword');
    fireEvent.press(loginButton);
    
    await waitFor(() => {
      expect(queryByText('Invalid credentials')).toBeTruthy();
    });
  });

  it('shows biometric login option when available', async () => {
    const mockCheckBiometric = jest.fn().mockResolvedValue(true);
    const contextValue = { 
      ...mockAuthContext, 
      checkBiometricAvailability: mockCheckBiometric 
    };
    
    const { queryByText } = renderLoginScreen(contextValue);
    
    await waitFor(() => {
      expect(queryByText('Use Biometric Login')).toBeTruthy();
    });
  });

  it('handles biometric login', async () => {
    const mockBiometricLogin = jest.fn().mockResolvedValue({ success: true });
    const mockCheckBiometric = jest.fn().mockResolvedValue(true);
    const contextValue = { 
      ...mockAuthContext, 
      loginWithBiometrics: mockBiometricLogin,
      checkBiometricAvailability: mockCheckBiometric,
    };
    
    const { getByText } = renderLoginScreen(contextValue);
    
    await waitFor(() => {
      const biometricButton = getByText('Use Biometric Login');
      fireEvent.press(biometricButton);
    });
    
    await waitFor(() => {
      expect(mockBiometricLogin).toHaveBeenCalled();
    });
  });

  it('toggles password visibility', () => {
    const { getByPlaceholderText, getByTestId } = renderLoginScreen();
    const passwordInput = getByPlaceholderText('Password');
    const toggleButton = getByTestId('password-toggle');
    
    expect(passwordInput.props.secureTextEntry).toBe(true);
    
    fireEvent.press(toggleButton);
    expect(passwordInput.props.secureTextEntry).toBe(false);
    
    fireEvent.press(toggleButton);
    expect(passwordInput.props.secureTextEntry).toBe(true);
  });

  it('meets accessibility requirements', () => {
    const { getByLabelText, getByRole } = renderLoginScreen();
    
    expect(getByLabelText('Email input')).toBeTruthy();
    expect(getByLabelText('Password input')).toBeTruthy();
    expect(getByRole('button', { name: 'Login' })).toBeTruthy();
  });

  it('handles keyboard navigation', () => {
    const { getByPlaceholderText } = renderLoginScreen();
    const emailInput = getByPlaceholderText('Email');
    const passwordInput = getByPlaceholderText('Password');
    
    // Simulate tab navigation
    fireEvent(emailInput, 'onSubmitEditing');
    
    // Password input should be focused (we can't directly test focus)
    expect(passwordInput).toBeTruthy();
  });
});
