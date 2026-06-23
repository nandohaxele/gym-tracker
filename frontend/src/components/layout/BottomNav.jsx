// BottomNav - mobile-first primary navigation with large tap targets.
// Sticky to the bottom, safe-area aware. Center action is an emphasized CTA.
// TODO (Phase 5+): wire the "Profile" tab and any future top-level sections.

import { NavLink } from 'react-router-dom';
import { Home, Plus, User } from 'lucide-react';
import { cn } from '@/lib/utils.js';

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 text-xs font-medium transition-colors',
          isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
        )
      }
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );
}

// `floating` (default) pins the nav to the viewport bottom. Pages that need the
// full height for editing (e.g. the workout editor) pass floating={false} so the
// nav flows after the content instead of covering it.
export default function BottomNav({ floating = true }) {
  return (
    <nav
      aria-label="Primary"
      className={cn(
        'border-t border-border bg-background/90 pb-safe backdrop-blur-md',
        floating ? 'fixed inset-x-0 bottom-0 z-30' : 'mt-auto w-full'
      )}
    >
      <div className="mx-auto flex w-full max-w-md items-stretch px-2">
        <NavItem to="/home" icon={Home} label="Home" />

        {/* Center CTA - new workout */}
        <div className="flex flex-1 items-center justify-center">
          <NavLink
            to="/workouts/new"
            aria-label="New workout"
            className="flex h-14 w-14 -translate-y-3 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/30 transition-transform active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <Plus className="h-6 w-6" aria-hidden="true" />
          </NavLink>
        </div>

        {/* Placeholder tab for a future profile/settings section. */}
        <button
          type="button"
          disabled
          aria-label="Profile (coming soon)"
          title="Coming soon"
          className="flex min-h-[56px] flex-1 cursor-not-allowed flex-col items-center justify-center gap-1 text-xs font-medium text-muted-foreground/50"
        >
          <User className="h-5 w-5" aria-hidden="true" />
          <span>Profile</span>
        </button>
      </div>
    </nav>
  );
}
