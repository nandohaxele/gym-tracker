// WorkoutEditorPage - create a new workout, or edit an existing one (route /workouts/:id/edit).
// Hosts the rest timer, exercise picker, and per-exercise SetRow editor.

import { useParams } from 'react-router-dom';

export default function WorkoutEditorPage() {
  const { id } = useParams();
  const isEditing = Boolean(id);

  // TODO:
  // - Local state for { name, date, exercises: [{ exercise_id, sets: [...] }] }.
  // - If editing, fetch via api/workouts.getWorkout(id) and hydrate.
  // - Add ExercisePicker (modal) + SetRow editors with reps/weight inputs.
  // - Mount RestTimer (frontend-only).
  // - Save button: createWorkout / updateWorkout.

  return (
    <main className="page">
      <h1>{isEditing ? 'Edit workout' : 'New workout'}</h1>
      {/* TODO: workout form */}
    </main>
  );
}
