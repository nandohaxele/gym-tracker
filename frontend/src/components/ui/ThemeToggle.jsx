import { Moon, Sun, MonitorSmartphone } from 'lucide-react';
import useTheme from '@/hooks/useTheme.js';
import { cn } from '@/lib/utils.js';

/**
 * ThemeToggle - cycles light -> dark -> system and shows the matching icon.
 * The accessible label announces the *next* action for screen-reader users.
 */
const NEXT_LABEL = {
  light: 'Switch to dark theme',
  dark: 'Switch to system theme',
  system: 'Switch to light theme',
};

export default function ThemeToggle({ className }) {
  const { theme, toggleTheme } = useTheme();

  const Icon = theme === 'dark' ? Moon : theme === 'system' ? MonitorSmartphone : Sun;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={NEXT_LABEL[theme]}
      title={NEXT_LABEL[theme]}
      className={cn(
        'inline-flex h-11 w-11 items-center justify-center rounded-lg text-foreground',
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        className
      )}
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
    </button>
  );
}
