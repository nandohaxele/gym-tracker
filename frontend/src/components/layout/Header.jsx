// Header - app title, theme toggle, logout button.

import useAuth from '../../hooks/useAuth.js';
import ThemeToggle from '../ui/ThemeToggle.jsx';

export default function Header() {
  const auth = useAuth();
  // TODO: Render brand on left, ThemeToggle + Logout on right.
  return (
    <header className="app-header">
      <span className="app-header__brand">Gym Tracker</span>
      <div className="app-header__actions">
        <ThemeToggle />
        <button type="button" className="btn btn--ghost" onClick={auth?.logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
