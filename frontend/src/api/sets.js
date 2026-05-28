// Sets API calls.
// Endpoints (api_contract.md): POST /sets, PUT /sets/{id}, DELETE /sets/{id}

import client from './axiosClient.js';

export async function createSet(payload) {
  // TODO: payload shape: { workout_exercise_id, reps, weight, order_index }
  return client.post('/sets', payload);
}

export async function updateSet(id, payload) {
  return client.put(`/sets/${id}`, payload);
}

export async function deleteSet(id) {
  return client.delete(`/sets/${id}`);
}
