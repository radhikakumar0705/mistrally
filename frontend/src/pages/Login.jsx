import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import authApi from "../api/auth";

const Login = () => {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await authApi.login(form);

      console.log("Login response:", res.data); // debug line

      const token = res.data?.access_token;
      if (!token) {
        throw new Error("No access_token returned from backend");
      }

      // Store token first
      localStorage.setItem("token", token);

      // Small delay ensures state update before redirect
      setTimeout(() => navigate("/chat"), 100);
    } catch (err) {
      console.error("Login error:", err);
      setError("Invalid credentials or server issue");
    }
  };

  return (
    <div className="min-h-screen flex justify-center items-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 shadow-lg rounded-lg w-80"
      >
        <h2 className="text-2xl font-semibold mb-6 text-center">Login</h2>
        {error && <p className="text-red-500 mb-4 text-sm">{error}</p>}

        <input
          type="text"
          name="username"
          placeholder="Username"
          className="w-full mb-3 px-3 py-2 border rounded"
          onChange={handleChange}
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          className="w-full mb-4 px-3 py-2 border rounded text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
          onChange={handleChange}
          required
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Login
        </button>
        <p className="text-sm mt-4 text-center">
          No account?{" "}
          <Link to="/signup" className="text-blue-500">
            Sign up
          </Link>
        </p>
      </form>
    </div>
  );
};

export default Login;
