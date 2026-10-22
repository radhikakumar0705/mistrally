import axiosClient, { API_BASE } from "./axiosClient";
import type { AuthSession, FeatureConfig, User } from "./types";

export interface Credentials {
  username: string;
  password: string;
}

export interface Registration extends Credentials {
  email: string;
}

const auth = {
  config: () => axiosClient.get<FeatureConfig>("/auth/config"),
  signup: (data: Registration) => axiosClient.post<{ message: string }>("/auth/register", data),
  login: (data: Credentials) => axiosClient.post<AuthSession>("/auth/login", data),
  getProfile: () => axiosClient.get<User>("/auth/profile"),
  // Full-page navigations: the backend redirects to Google and back
  googleLoginUrl: () => `${API_BASE}/auth/google/login`,
  googleLinkUrl: () => `${API_BASE}/auth/google/login?intent=link`,
};

export default auth;
