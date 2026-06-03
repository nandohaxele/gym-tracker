// Auth context: owns the JWT + current user and exposes login/register/logout.
// - Token is persisted in localStorage via utils/storage.js.
// - On mount we hydrate the user from /auth/me if a token exists.
// - A global 'auth:unauthorized' event (dispatched by axiosClient on 401)
//   resets state so an expired/invalid token can't keep us "logged in".

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { getToken, setToken, clearToken } from '../utils/storage.js';
import * as authApi from '../api/auth.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken());
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyLogout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setUser(null);
  }, []);

  // Hydrate on mount: if a token is present, validate it by loading the user.
  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const existing = getToken();
      if (!existing) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (!cancelled) {
          setTokenState(existing);
          setUser(me);
        }
      } catch {
        // Token invalid/expired -> drop it.
        if (!cancelled) applyLogout();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [applyLogout]);

  // React to global 401s (e.g. token expired mid-session).
  useEffect(() => {
    const onUnauthorized = () => applyLogout();
    window.addEventListener('auth:unauthorized', onUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized);
  }, [applyLogout]);

  const login = useCallback(async ({ email, password }) => {
    // Persist the token first so the axios interceptor can attach it to /me.
    const { access_token: accessToken } = await authApi.login({ email, password });
    setToken(accessToken);
    setTokenState(accessToken);

    const me = await authApi.me();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(
    async ({ email, password }) => {
      await authApi.register({ email, password });
      // Backend returns the created user but not a token, so log in to obtain one.
      return login({ email, password });
    },
    [login]
  );

  const logout = useCallback(() => {
    applyLogout();
  }, [applyLogout]);

  const value = useMemo(
    () => ({
      token,
      user,
      isLoading,
      isAuthenticated: Boolean(token),
      login,
      register,
      logout,
    }),
    [token, user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
