// WorkoutList - vertical list of WorkoutCard items.
// Empty / loading / error states are handled by the page (HomePage) so this
// component stays a pure presentational list.

import WorkoutCard from './WorkoutCard.jsx';

export default function WorkoutList({ workouts = [] }) {
  return (
    <ul className="flex flex-col gap-3">
      {workouts.map((w) => (
        <li key={w.id}>
          <WorkoutCard workout={w} />
        </li>
      ))}
    </ul>
  );
}
