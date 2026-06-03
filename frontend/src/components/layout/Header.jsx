// Header - brand on the left, theme toggle + logout on the right.
// Sticky + safe-area aware so it sits flush under the status bar.

import { Dumbbell, LogOut } from 'lucide-react';
import useAuth from '@/hooks/useAuth.js';
import ThemeToggle from '@/components/ui/ThemeToggle.jsx';

export default function Header() {
  const { logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 pt-safe backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-md items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Dumbbell className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-base font-bold tracking-tight">Gym Tracker</span>
        </div>

        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            type="button"
            onClick={logout}
            aria-label="Log out"
            title="Log out"
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <LogOut className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>
  );
}
