import axios from "axios";
import { clearStoredAuth, getToken } from "../lib/authStorage";

// Same-origin /api by default: Vite proxies it in development, nginx in Docker/Kubernetes
export const API_BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

const axiosClient = axios.create({ baseURL: API_BASE });

export const authHeader = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// An expired or invalid token sends the user back to login
export const handleUnauthorized = () => {
  clearStoredAuth();
  if (window.location.pathname !== "/login") window.location.assign("/login?expired=1");
};

axiosClient.interceptors.request.use((config) => {
  Object.assign(config.headers, authHeader());
  return config;
});

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthRequest = error.config?.url?.startsWith("/auth/");
    if (error.response?.status === 401 && !isAuthRequest) handleUnauthorized();
    return Promise.reject(error);
  }
);

// Prefer the backend's error message when there is one
export const errorMessage = (error, fallback) =>
  error?.response?.data?.error || error?.message || fallback;

export default axiosClient;
