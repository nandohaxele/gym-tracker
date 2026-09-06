// Granular Set APIs (Phase 5 surface).
// POST /sets and PUT /sets/{id} do not exist — do not reintroduce them.

import client from './axiosClient.js';

export async function createSet(workoutExerciseId, payload) {
  return client.post(`/workout-exercises/${workoutExerciseId}/sets`, payload);
}

export async function patchSet(setId, payload) {
  return client.patch(`/sets/${setId}`, payload);
}

export async function deleteSet(setId) {
  return client.delete(`/sets/${setId}`);
}

export async function reorderSets(workoutExerciseId, ids) {
  return client.post(`/workout-exercises/${workoutExerciseId}/sets/reorder`, {
    ids,
  });
}
