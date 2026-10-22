import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { PageSpinner } from "../components/ProtectedRoute";
import { useAuth } from "../context/AuthContext";

/** Google redirects here after sign-in; the refresh cookie is already set, so we just pick up a session. */
export default function AuthCallback() {
  const { completeOAuth } = useAuth();
  const navigate = useNavigate();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // StrictMode runs effects twice in development
    started.current = true;
    completeOAuth()
      .then(() => navigate("/chat", { replace: true }))
      .catch(() => navigate("/login?error=google_failed", { replace: true }));
  }, [completeOAuth, navigate]);

  return <PageSpinner />;
}
