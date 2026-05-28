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
  // TODO: read token from storage and attach to Authorization header.
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: unwrap {success, data, error} and handle 401 globally.
axiosClient.interceptors.response.use(
  (response) => {
    // TODO: Per api_contract.md the body is { success, data, error }.
    //       Return response.data.data on success, throw response.data.error on failure.
    const body = response.data;
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) return body.data;
      throw new Error(body.error || 'Request failed');
    }
    return body;
  },
  (error) => {
    // TODO: On 401, clear the stored token and redirect to /login.
    if (error.response?.status === 401) {
      clearToken();
      // TODO: trigger a redirect or auth-context logout signal.
    }
    const apiError = error.response?.data?.error;
    return Promise.reject(new Error(apiError || error.message));
  }
);

export default axiosClient;
