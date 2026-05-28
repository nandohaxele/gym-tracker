// useAuth - thin hook that consumes AuthContext.

import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext.jsx';

export default function useAuth() {
  // TODO: throw if used outside <AuthProvider>?
  return useContext(AuthContext);
}
