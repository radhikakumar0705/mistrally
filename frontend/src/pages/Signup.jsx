import { Loader2, Lock, Mail, User } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import auth from "../api/auth";
import { errorMessage } from "../api/axiosClient";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import GoogleButton, { OrDivider } from "../components/GoogleButton";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, googleEnabled } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await auth.signup(form);
      // Log straight in so new users land in the chat
      const { data } = await auth.login({ username: form.username, password: form.password });
      login(data.access_token, data.user);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Signup failed. Try again."));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Your chats and documents stay on your own server."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-violet-300 hover:text-violet-200">
            Log in
          </Link>
        </>
      }
    >
      {googleEnabled ? (
        <>
          <GoogleButton label="Sign up with Google" />
          <OrDivider />
        </>
      ) : null}
      <form onSubmit={handleSubmit} className="space-y-4">
        {error ? (
          <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}
        <FormField
          label="Username"
          icon={User}
          name="username"
          autoComplete="username"
          placeholder="yourname"
          maxLength={50}
          value={form.username}
          onChange={handleChange}
          required
          autoFocus
        />
        <FormField
          label="Email"
          icon={Mail}
          type="email"
          name="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={handleChange}
          required
        />
        <FormField
          label="Password"
          icon={Lock}
          type="password"
          name="password"
          autoComplete="new-password"
          placeholder="••••••••"
          minLength={8}
          hint="At least 8 characters."
          value={form.password}
          onChange={handleChange}
          required
        />
        <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
