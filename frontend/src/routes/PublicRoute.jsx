// Guards public-only routes (login / register):
// - while auth is hydrating, show the branded loader
// - if already authenticated, bounce to where the user was headed (or /home)

import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '@/hooks/useAuth.js';
import LoadingScreen from '@/components/ui/LoadingScreen.jsx';

export default function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingScreen label="Loading…" />;
  }

  if (isAuthenticated) {
    const redirectTo = location.state?.from?.pathname || '/home';
    return <Navigate to={redirectTo} replace />;
  }

  return children;
}
