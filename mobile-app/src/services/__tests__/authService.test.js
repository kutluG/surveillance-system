import { authService } from '../authService';
import secureStorage from '../../utils/secureStorage';

// Mock secure storage
jest.mock('../../utils/secureStorage');
const mockSecureStorage = secureStorage;

// Mock fetch globally
global.fetch = jest.fn();

describe('authService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSecureStorage.setItem.mockResolvedValue();
    mockSecureStorage.getItem.mockResolvedValue(null);
    mockSecureStorage.removeItem.mockResolvedValue();
  });

  describe('login', () => {
    it('successfully logs in with valid credentials', async () => {
      const mockResponse = {
        token: 'mock-jwt-token',
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await authService.login('test@example.com', 'password123');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith('auth_token', 'mock-jwt-token');
    });

    it('throws error for invalid credentials', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Invalid credentials' }),
      });

      await expect(
        authService.login('test@example.com', 'wrongpassword')
      ).rejects.toThrow('Invalid credentials');
    });

    it('handles network errors', async () => {
      fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        authService.login('test@example.com', 'password123')
      ).rejects.toThrow('Network error');
    });
  });

  describe('logout', () => {
    it('successfully logs out', async () => {      // Set up initial token
      mockSecureStorage.getItem.mockResolvedValue('mock-token');

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Logged out successfully' }),
      });

      await authService.logout();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/logout'),
        expect.objectContaining({
          method: 'POST',        headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
          }),
        })
      );

      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('auth_token');
    });

    it('handles logout errors gracefully', async () => {
      fetch.mockRejectedValueOnce(new Error('Logout failed'));      await expect(authService.logout()).resolves.not.toThrow();
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('auth_token');
    });
  });

  describe('getCurrentUser', () => {
    it('returns user data when authenticated', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',      };

      mockSecureStorage.getItem.mockResolvedValue('mock-token');

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      });

      const result = await authService.getCurrentUser();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
          }),
        })
      );

      expect(result).toEqual(mockUser);
    });

    it('returns null when not authenticated', async () => {
      const result = await authService.getCurrentUser();
      expect(result).toBeNull();
    });

    it('handles invalid token', async () => {
      mockSecureStorage.getItem.mockResolvedValue('invalid-token');

      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Invalid token' }),
      });

      const result = await authService.getCurrentUser();

      expect(result).toBeNull();
      expect(mockSecureStorage.removeItem).toHaveBeenCalledWith('auth_token');
    });
  });

  describe('refreshToken', () => {
    it('successfully refreshes token', async () => {
      const mockResponse = {
        token: 'new-jwt-token',
        expiresIn: 3600,
      };

      mockSecureStorage.getItem.mockResolvedValue('old-token');

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await authService.refreshToken();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/refresh'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer old-token',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(mockSecureStorage.setItem).toHaveBeenCalledWith('auth_token', 'new-jwt-token');
    });

    it('throws error when refresh fails', async () => {
      mockSecureStorage.getItem.mockResolvedValue('old-token');

      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Refresh failed' }),
      });

      await expect(authService.refreshToken()).rejects.toThrow('Refresh failed');
    });
  });

  describe('isAuthenticated', () => {
    it('returns true when token exists', async () => {
      mockSecureStorage.getItem.mockResolvedValue('mock-token');
      const result = await authService.isAuthenticated();
      expect(result).toBe(true);
    });

    it('returns false when no token exists', async () => {
      const result = await authService.isAuthenticated();
      expect(result).toBe(false);
    });
  });

  describe('getToken', () => {
    it('returns stored token', async () => {
      mockSecureStorage.getItem.mockResolvedValue('mock-token');
      const result = await authService.getToken();
      expect(result).toBe('mock-token');
    });

    it('returns null when no token stored', async () => {
      const result = await authService.getToken();
      expect(result).toBeNull();
    });
  });

  describe('updateProfile', () => {
    it('successfully updates user profile', async () => {
      const mockUpdatedUser = {
        id: '1',
        email: 'test@example.com',
        name: 'Updated Name',
      };

      mockSecureStorage.getItem.mockResolvedValue('mock-token');

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedUser,
      });

      const result = await authService.updateProfile({
        name: 'Updated Name',
      });

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/profile'),
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ name: 'Updated Name' }),
        })
      );

      expect(result).toEqual(mockUpdatedUser);
    });
  });

  describe('changePassword', () => {
    it('successfully changes password', async () => {
      mockSecureStorage.getItem.mockResolvedValue('mock-token');

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Password changed successfully' }),
      });

      const result = await authService.changePassword(
        'oldpassword',
        'newpassword'
      );

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/change-password'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({
            currentPassword: 'oldpassword',
            newPassword: 'newpassword',
          }),
        })
      );

      expect(result.message).toBe('Password changed successfully');
    });

    it('throws error for incorrect current password', async () => {
      mockSecureStorage.getItem.mockResolvedValue('mock-token');

      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ message: 'Current password is incorrect' }),
      });

      await expect(
        authService.changePassword('wrongpassword', 'newpassword')
      ).rejects.toThrow('Current password is incorrect');
    });
  });
});
