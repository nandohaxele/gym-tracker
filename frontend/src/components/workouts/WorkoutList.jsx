// WorkoutList - vertical list of WorkoutCard items.

import WorkoutCard from './WorkoutCard.jsx';

export default function WorkoutList({ workouts = [] }) {
  // TODO: empty state + skeleton loaders.
  if (!workouts.length) {
    return <p className="empty">No workouts yet. Tap + Workout to get started.</p>;
  }
  return (
    <ul className="workout-list">
      {workouts.map((w) => (
        <li key={w.id}>
          <WorkoutCard workout={w} />
        </li>
      ))}
    </ul>
  );
}
