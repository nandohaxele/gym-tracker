// Exercises API calls.
// Endpoint (api_contract.md): GET /exercises

import client from './axiosClient.js';

export async function listExercises() {
  // TODO: return the seeded catalog ordered by muscle_group/name.
  return client.get('/exercises');
}
