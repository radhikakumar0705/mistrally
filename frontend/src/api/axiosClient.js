import axios from "axios";
import { clearStoredAuth, getToken, readCookie, setSessionHint, setToken } from "../lib/authStorage";

// Same-origin /api by default: Vite proxies it in development, nginx in Docker/Kubernetes
export const API_BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

const axiosClient = axios.create({ baseURL: API_BASE, withCredentials: true });

export const authHeader = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const csrfHeader = () => ({ "X-CSRF-TOKEN": readCookie("csrf_refresh_token") || "" });

// Listeners (the AuthContext) learn about refreshed users and ended sessions
const listeners = new Set();
export const onAuthChange = (listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};
const emit = (event) => listeners.forEach((listener) => listener(event));

/**
 * Trade the refresh cookie for a new access token. Concurrent callers share one request,
 * because the server rotates the refresh token and a second parallel use would look like a replay.
 */
let refreshing = null;
export function refreshSession() {
  if (!refreshing) {
    refreshing = axios
      .post(`${API_BASE}/auth/refresh`, null, { headers: csrfHeader(), withCredentials: true })
      .then(({ data }) => {
        setToken(data.access_token);
        setSessionHint(true);
        emit({ type: "refreshed", user: data.user });
        return data;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export function endSession({ expired = false } = {}) {
  clearStoredAuth();
  emit({ type: "ended" });
  if (expired && window.location.pathname !== "/login") window.location.assign("/login?expired=1");
}

export const logoutRequest = () =>
  axios.post(`${API_BASE}/auth/logout`, null, { headers: csrfHeader(), withCredentials: true });

axiosClient.interceptors.request.use((config) => {
  Object.assign(config.headers, authHeader());
  return config;
});

// An expired access token is refreshed once and the request retried; if that fails, the session is over
axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isAuthRequest = config?.url?.startsWith("/auth/");
    if (response?.status === 401 && !isAuthRequest && !config._retried) {
      try {
        await refreshSession();
        return axiosClient({ ...config, _retried: true });
      } catch {
        endSession({ expired: true });
      }
    }
    return Promise.reject(error);
  }
);

// Prefer the backend's error message when there is one
export const errorMessage = (error, fallback) =>
  error?.response?.data?.error || error?.message || fallback;

export default axiosClient;
