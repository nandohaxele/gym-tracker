// useTheme - consume ThemeContext. Throws if used outside <ThemeProvider>.

import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext.jsx';

export default function useTheme() {
  const ctx = useContext(ThemeContext);
  if (ctx === null) {
    throw new Error('useTheme must be used within a <ThemeProvider>');
  }
  return ctx;
}
