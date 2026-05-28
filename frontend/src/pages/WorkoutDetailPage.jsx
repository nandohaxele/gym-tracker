// WorkoutDetailPage - read-only view of a saved workout.

import { useParams, Link } from 'react-router-dom';

export default function WorkoutDetailPage() {
  const { id } = useParams();

  // TODO:
  // - Fetch workout via api/workouts.getWorkout(id).
  // - Render exercises + sets in a clean read-only layout.
  // - "Edit" button -> /workouts/:id/edit. "Delete" button -> confirm + deleteWorkout.

  return (
    <main className="page">
      <h1>Workout #{id}</h1>
      <Link to={`/workouts/${id}/edit`} className="btn">Edit</Link>
      {/* TODO: exercises + sets read-only */}
    </main>
  );
}
