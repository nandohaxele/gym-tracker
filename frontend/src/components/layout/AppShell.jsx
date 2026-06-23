// AppShell - layout for protected routes: sticky header, scrollable content,
// sticky bottom navigation. Mobile-first, safe-area aware (Galaxy S21 / notch).

import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header.jsx';
import BottomNav from './BottomNav.jsx';
import { cn } from '@/lib/utils.js';

// The workout editor (/workouts/new, /workouts/:id/edit) frees up vertical
// space by letting the BottomNav flow at the end of the content instead of
// staying pinned over the form.
function isEditorRoute(pathname) {
  return pathname === '/workouts/new' || pathname.endsWith('/edit');
}

export default function AppShell() {
  const { pathname } = useLocation();
  const floatingNav = !isEditorRoute(pathname);

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <Header />

      <main className={cn('flex-1 animate-fade-in pt-4', floatingNav ? 'pb-24' : 'pb-8')}>
        <Outlet />
      </main>

      <BottomNav floating={floatingNav} />
    </div>
  );
}
