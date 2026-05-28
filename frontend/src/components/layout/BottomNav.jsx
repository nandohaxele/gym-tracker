// BottomNav - mobile-first navigation, large tap targets (>=44px).

import { NavLink } from 'react-router-dom';

export default function BottomNav() {
  // TODO: Replace with icons; ensure each tab has min-height 56px for thumb taps.
  return (
    <nav className="bottom-nav" aria-label="Primary">
      <NavLink to="/home" className="bottom-nav__item">Home</NavLink>
      <NavLink to="/workouts/new" className="bottom-nav__item">+ Workout</NavLink>
    </nav>
  );
}
