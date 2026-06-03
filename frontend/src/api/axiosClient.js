// Centralized Axios instance + interceptors.
// All other api/*.js modules import from here.

import axios from 'axios';
import { getToken, clearToken } from '../utils/storage.js';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

const axiosClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach JWT bearer if present.
axiosClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: unwrap {success, data, error} and handle 401 globally.
axiosClient.interceptors.response.use(
  (response) => {
    // Per api_contract.md the body is { success, data, error }.
    const body = response.data;
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) return body.data;
      throw new Error(body.error || 'Request failed');
    }
    return body;
  },
  (error) => {
    // On 401, drop the stored token and signal the app so AuthContext can
    // reset state and route guards can redirect to /login.
    if (error.response?.status === 401) {
      clearToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
    }
    const apiError = error.response?.data?.error;
    return Promise.reject(new Error(apiError || error.message));
  }
);

export default axiosClient;
