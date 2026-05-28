// Auth context: holds the current user + JWT token, exposes login/logout/register.
// Persists the token in localStorage via utils/storage.js.

import { createContext, useEffect, useState } from 'react';
import { getToken, setToken, clearToken } from '../utils/storage.js';
import * as authApi from '../api/auth.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // TODO: holds { token, user, isLoading } and exposes { login, register, logout }.
  const [token, setTokenState] = useState(() => getToken());
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // TODO: On mount, if token exists, fetch /auth/me and hydrate user. Else stop loading.
    setIsLoading(false);
  }, []);

  const login = async ({ email, password }) => {
    // TODO:
    //   const { access_token } = await authApi.login({ email, password });
    //   setToken(access_token); setTokenState(access_token);
    //   const me = await authApi.me(); setUser(me);
  };

  const register = async ({ email, password }) => {
    // TODO:
    //   await authApi.register({ email, password });
    //   await login({ email, password });
  };

  const logout = () => {
    // TODO: clearToken(); setTokenState(null); setUser(null);
    clearToken();
    setTokenState(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
