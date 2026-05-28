// ThemeToggle - flips light/dark via ThemeContext.

import useTheme from '../../hooks/useTheme.js';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme() || {};
  // TODO: Replace text with sun/moon icon.
  return (
    <button
      type="button"
      className="btn btn--ghost"
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
    >
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  );
}
