// Auth API calls.
// Endpoints (api_contract.md): POST /auth/register, POST /auth/login, GET /auth/me

import client from './axiosClient.js';

export async function register({ email, password }) {
  // TODO: return client.post('/auth/register', { email, password });
  return client.post('/auth/register', { email, password });
}

export async function login({ email, password }) {
  // TODO: return client.post('/auth/login', { email, password });
  return client.post('/auth/login', { email, password });
}

export async function me() {
  // TODO: return client.get('/auth/me');
  return client.get('/auth/me');
}
