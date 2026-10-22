// The access token lives only in memory (never localStorage), so injected scripts can't read it
// back later. The refresh token is an httpOnly cookie the browser sends to /api/auth/refresh.
let accessToken: string | null = null;

// Remembers that this browser has a session, so anonymous visitors don't trigger a refresh call
const SESSION_HINT_KEY = "sockrat:session";

export const getToken = (): string | null => accessToken;
export const setToken = (token: string | null): void => {
  accessToken = token;
};

export const hasSessionHint = (): boolean => {
  try {
    return localStorage.getItem(SESSION_HINT_KEY) === "1";
  } catch {
    return false;
  }
};

export const setSessionHint = (on: boolean): void => {
  try {
    if (on) localStorage.setItem(SESSION_HINT_KEY, "1");
    else localStorage.removeItem(SESSION_HINT_KEY);
  } catch {
    // storage blocked; we just try a refresh on every load instead
  }
};

export const clearStoredAuth = (): void => {
  accessToken = null;
  setSessionHint(false);
  try {
    // tokens stored by older versions of the app
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  } catch {
    // ignore
  }
};

export const readCookie = (name: string): string | undefined =>
  document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.slice(name.length + 1);
