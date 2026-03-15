import axios, { type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management utilities
export const tokenStorage = {
  getAccessToken: (): string | null => {
    return localStorage.getItem('access_token');
  },
  setAccessToken: (token: string): void => {
    localStorage.setItem('access_token', token);
  },
  getRefreshToken: (): string | null => {
    return localStorage.getItem('refresh_token');
  },
  setRefreshToken: (token: string): void => {
    localStorage.setItem('refresh_token', token);
  },
  clearTokens: (): void => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  setTokens: (accessToken: string, refreshToken: string): void => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },
};

// Flag to prevent multiple refresh requests
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

// Function to refresh token
const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = tokenStorage.getRefreshToken();

  if (!refreshToken) {
    tokenStorage.clearTokens();
    window.location.href = '/login';
    return null;
  }

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_URL || '/api/v1'}/auth/refresh`,
      { refresh_token: refreshToken }
    );

    const { access_token: newAccessToken } = response.data;
    tokenStorage.setAccessToken(newAccessToken);

    return newAccessToken;
  } catch {
    // Refresh failed, clear tokens and redirect to login
    tokenStorage.clearTokens();
    window.location.href = '/login';
    return null;
  }
};

// Request interceptor to add authentication token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error: unknown) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Prevent multiple simultaneous refresh requests
      if (isRefreshing) {
        try {
          const newToken = await refreshPromise;
          if (newToken && originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      } else {
        isRefreshing = true;
        refreshPromise = refreshAccessToken();

        try {
          const newToken = await refreshPromise;
          if (newToken && originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
          refreshPromise = null;
        }
      }
    }

    return Promise.reject(error);
  }
);

export default api;