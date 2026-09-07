// Tiny localStorage wrapper for the JWT token and the theme preference.
// Centralized here so we never sprinkle raw localStorage keys across the app.

const TOKEN_KEY = 'gym.token';
const THEME_KEY = 'gym.theme';

export function getToken() {
  // TODO: consider migrating to httpOnly cookie if/when the API supports it.
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore quota / privacy mode */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export function getTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

export function setTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* ignore */
  }
}

const ASSISTANT_LOCALE_KEY = 'gym.assistantLocale';

export function getAssistantLocale() {
  try {
    return localStorage.getItem(ASSISTANT_LOCALE_KEY);
  } catch {
    return null;
  }
}

export function setAssistantLocale(locale) {
  try {
    localStorage.setItem(ASSISTANT_LOCALE_KEY, locale);
  } catch {
    /* ignore */
  }
}
