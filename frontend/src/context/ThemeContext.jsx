// Theme context: 'light' | 'dark' | 'system'.
// - Persists the preference in localStorage (key 'gym.theme').
// - Resolves 'system' against prefers-color-scheme and reacts to OS changes.
// - Applies the `.dark` class on <html> (Tailwind darkMode: 'class').
// The anti-FOUC script in index.html mirrors this logic for the first paint.

import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { getTheme, setTheme as persistTheme } from '../utils/storage.js';

export const ThemeContext = createContext(null);

const THEMES = ['light', 'dark', 'system'];
const DARK_QUERY = '(prefers-color-scheme: dark)';

function getSystemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light';
}

function resolve(theme, systemTheme) {
  return theme === 'system' ? systemTheme : theme;
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    const stored = getTheme();
    return THEMES.includes(stored) ? stored : 'system';
  });
  const [systemTheme, setSystemTheme] = useState(getSystemTheme);

  // Keep systemTheme in sync with the OS when the user follows the system.
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const mql = window.matchMedia(DARK_QUERY);
    const onChange = (e) => setSystemTheme(e.matches ? 'dark' : 'light');
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme = resolve(theme, systemTheme);

  // Apply the resolved theme to <html> and persist the preference.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark');
    persistTheme(theme);
  }, [theme, resolvedTheme]);

  const setTheme = useCallback((next) => {
    if (THEMES.includes(next)) setThemeState(next);
  }, []);

  // Cycle: light -> dark -> system -> light.
  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const idx = THEMES.indexOf(prev);
      return THEMES[(idx + 1) % THEMES.length];
    });
  }, []);

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme, toggleTheme }),
    [theme, resolvedTheme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
