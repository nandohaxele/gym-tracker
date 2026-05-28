// Theme context: light / dark, persisted in localStorage.
// Applies data-theme attribute on <html> so theme.css variables switch.

import { createContext, useEffect, useState } from 'react';
import { getTheme, setTheme as persistTheme } from '../utils/storage.js';

export const ThemeContext = createContext(null);

const DEFAULT_THEME = 'light';

export function ThemeProvider({ children }) {
  // TODO: read initial theme from storage; fall back to prefers-color-scheme.
  const [theme, setTheme] = useState(() => getTheme() || DEFAULT_THEME);

  useEffect(() => {
    // TODO: apply data-theme on <html>, persist to localStorage.
    document.documentElement.setAttribute('data-theme', theme);
    persistTheme(theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
