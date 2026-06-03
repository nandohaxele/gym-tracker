// AppShell - layout for protected routes: sticky header, scrollable content,
// sticky bottom navigation. Mobile-first, safe-area aware (Galaxy S21 / notch).

import { Outlet } from 'react-router-dom';
import Header from './Header.jsx';
import BottomNav from './BottomNav.jsx';

export default function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <Header />

      <main className="flex-1 animate-fade-in pb-24 pt-4">
        <Outlet />
      </main>

      <BottomNav />
    </div>
  );
}
