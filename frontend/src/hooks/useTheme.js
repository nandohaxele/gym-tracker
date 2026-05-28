// useTheme - thin hook that consumes ThemeContext.

import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext.jsx';

export default function useTheme() {
  // TODO: throw if used outside <ThemeProvider>?
  return useContext(ThemeContext);
}
