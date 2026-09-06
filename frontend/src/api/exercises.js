// Exercises API. List is active globals + the caller's personal exercises.

import client from './axiosClient.js';

export async function listExercises() {
  return client.get('/exercises');
}

export async function createExercise(payload) {
  return client.post('/exercises', payload);
}

export async function getLastWeights(exerciseIds, excludeWorkoutId) {
  const ids = (exerciseIds || []).filter((id) => Number(id) > 0);
  if (ids.length === 0) return [];
  const params = { ids: ids.join(',') };
  if (excludeWorkoutId) params.exclude_workout_id = excludeWorkoutId;
  return client.get('/exercises/last-weights', { params });
}
