// AppShell - layout for protected routes: header on top, page content, bottom nav.
// Mobile-first container sized for Galaxy S21 (360x800) but works wider.

import { Outlet } from 'react-router-dom';
import Header from './Header.jsx';
import BottomNav from './BottomNav.jsx';

export default function AppShell() {
  // TODO: Wrap children in safe-area-aware container.
  return (
    <div className="app-shell">
      <Header />
      <div className="app-shell__content">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
}
