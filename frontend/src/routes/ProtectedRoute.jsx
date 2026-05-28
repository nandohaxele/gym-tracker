// Route guard: redirects to /login if there is no JWT in storage / context.

import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '../hooks/useAuth.js';

export default function ProtectedRoute({ children }) {
  // TODO: const { token, isLoading } = useAuth();
  // TODO: if (isLoading) return null;  // or a spinner
  // TODO: if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  const auth = useAuth();
  const location = useLocation();

  if (!auth?.token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}
