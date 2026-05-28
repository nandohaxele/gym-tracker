// Workouts API calls.
// Endpoints (api_contract.md):
//   GET    /workouts
//   POST   /workouts
//   GET    /workouts/{id}
//   PUT    /workouts/{id}
//   DELETE /workouts/{id}

import client from './axiosClient.js';

export async function listWorkouts() {
  // TODO: paginate later if needed.
  return client.get('/workouts');
}

export async function getWorkout(id) {
  return client.get(`/workouts/${id}`);
}

export async function createWorkout(payload) {
  // TODO: payload shape: { name, date?, exercises: [{ exercise_id, sets: [...] }] }
  return client.post('/workouts', payload);
}

export async function updateWorkout(id, payload) {
  return client.put(`/workouts/${id}`, payload);
}

export async function deleteWorkout(id) {
  return client.delete(`/workouts/${id}`);
}
