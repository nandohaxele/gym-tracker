// WorkoutCard - one row in the history list. Tappable, large hit area.

import { Link } from 'react-router-dom';
import { formatDate } from '../../utils/format.js';

export default function WorkoutCard({ workout }) {
  // TODO: Show name, formatted date, exercise count, total set count.
  return (
    <Link to={`/workouts/${workout.id}`} className="workout-card">
      <div className="workout-card__title">{workout.name}</div>
      <div className="workout-card__meta">
        {formatDate(workout.date)}
        {/* TODO: exercises count and sets count summary */}
      </div>
    </Link>
  );
}
