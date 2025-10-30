// src/components/NavBar.jsx
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const Navbar = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsLoggedIn(!!token); // true if token exists
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setIsLoggedIn(false);
    navigate("/login");
  };

  return (
    <nav className="flex justify-between items-center bg-gray-900 text-white px-6 py-4">
      <Link to="/" className="text-2xl font-bold text-purple-400">
        Mistrally
      </Link>

      {isLoggedIn ? (
        <button
          onClick={handleLogout}
          className="bg-red-500 px-4 py-2 rounded hover:bg-red-600 transition"
        >
          Logout
        </button>
      ) : (
        <button
          onClick={() => navigate("/login")}
          className="bg-blue-500 px-4 py-2 rounded hover:bg-blue-600 transition"
        >
          Login
        </button>
      )}
    </nav>
  );
};

export default Navbar;
