// Guards protected routes:
// - while auth is hydrating, show the branded loader (avoids redirect flicker)
// - if unauthenticated, redirect to /login and remember where we came from

import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '@/hooks/useAuth.js';
import LoadingScreen from '@/components/ui/LoadingScreen.jsx';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingScreen label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
