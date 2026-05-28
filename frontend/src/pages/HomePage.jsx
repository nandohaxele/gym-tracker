// HomePage - workout history list + "New workout" CTA.

import { Link } from 'react-router-dom';
import WorkoutList from '../components/workouts/WorkoutList.jsx';

export default function HomePage() {
  // TODO:
  // - useEffect: fetch workouts via api/workouts.listWorkouts.
  // - Render <WorkoutList workouts={...} /> + a sticky "New Workout" CTA.
  return (
    <main className="page">
      <header className="page__header">
        <h1>Workouts</h1>
        <Link to="/workouts/new" className="btn btn--primary">
          + New
        </Link>
      </header>
      <WorkoutList workouts={[]} />
    </main>
  );
}
