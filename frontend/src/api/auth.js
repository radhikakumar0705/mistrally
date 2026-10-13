import axiosClient, { API_BASE } from "./axiosClient";

const auth = {
  config: () => axiosClient.get("/auth/config"),
  signup: (data) => axiosClient.post("/auth/register", data),
  login: (data) => axiosClient.post("/auth/login", data),
  getProfile: () => axiosClient.get("/auth/profile"),
  // Full-page navigations: the backend redirects to Google and back
  googleLoginUrl: () => `${API_BASE}/auth/google/login`,
  googleLinkUrl: () => `${API_BASE}/auth/google/login?intent=link`,
};

export default auth;
