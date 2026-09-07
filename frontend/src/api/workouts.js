// Workouts / Session API.
// Live Session edits use PATCH + granular child routes. Backend PUT remains
// as unused compatibility debt and is not called from the frontend.

import client from './axiosClient.js';

export async function listWorkouts() {
  return client.get('/workouts');
}

export async function getWorkout(id) {
  return client.get(`/workouts/${id}`);
}

export async function createWorkout(payload) {
  return client.post('/workouts', payload);
}

export async function patchWorkout(id, payload) {
  return client.patch(`/workouts/${id}`, payload);
}

export async function deleteWorkout(id) {
  return client.delete(`/workouts/${id}`);
}

export async function completeWorkout(id) {
  return client.post(`/workouts/${id}/complete`);
}

export async function addWorkoutExercise(workoutId, payload) {
  return client.post(`/workouts/${workoutId}/exercises`, payload);
}

export async function deleteWorkoutExercise(workoutExerciseId) {
  return client.delete(`/workout-exercises/${workoutExerciseId}`);
}

export async function saveWorkoutAsTemplate(workoutId, name) {
  const body = name ? { name } : undefined;
  return client.post(`/workouts/${workoutId}/save-as-template`, body);
}
