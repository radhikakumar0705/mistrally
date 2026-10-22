import { Loader2, Lock, User } from "lucide-react";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import authApi from "../api/auth";
import { errorMessage } from "../api/axiosClient";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import GoogleButton, { OrDivider } from "../components/GoogleButton";
import { useAuth } from "../context/AuthContext";

const OAUTH_ERRORS: Record<string, string> = {
  account_exists:
    "An account with this email already exists. Log in with your password, then connect Google from the account menu.",
  google_failed: "Google sign-in didn't complete. Please try again.",
  google_unverified: "Your Google email address isn't verified.",
  google_disabled: "Google sign-in isn't available right now.",
  session_expired: "Your session expired. Please log in again.",
};

export default function Login() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, googleEnabled } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const { data } = await authApi.login(form);
      login(data.access_token, data.user);
      navigate(location.state?.from?.pathname || "/chat", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Invalid credentials or server issue"));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to continue learning with sockRat."
      footer={
        <>
          No account?{" "}
          <Link to="/signup" className="font-medium text-violet-300 hover:text-violet-200">
            Create one
          </Link>
        </>
      }
    >
      {googleEnabled ? (
        <>
          <GoogleButton />
          <OrDivider />
        </>
      ) : null}
      <form onSubmit={handleSubmit} className="space-y-4">
        {params.get("error") && !error ? (
          <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {OAUTH_ERRORS[params.get("error") ?? ""] || "Sign-in failed. Please try again."}
          </p>
        ) : null}
        {params.get("expired") && !error ? (
          <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Your session expired. Please log in again.
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}
        <FormField
          label="Username or email"
          icon={User}
          name="username"
          autoComplete="username"
          placeholder="yourname or you@example.com"
          value={form.username}
          onChange={handleChange}
          required
          autoFocus
        />
        <FormField
          label="Password"
          icon={Lock}
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={form.password}
          onChange={handleChange}
          required
        />
        <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? "Logging in…" : "Log in"}
        </button>
      </form>
    </AuthLayout>
  );
}
