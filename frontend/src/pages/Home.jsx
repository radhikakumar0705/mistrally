import React from "react";
import { useNavigate } from "react-router-dom";

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
      <div className="flex flex-col items-center justify-center text-center px-6 py-20">
        <h1 className="text-5xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
          Welcome to Mistrally
        </h1>
        <p className="text-lg text-gray-300 max-w-xl mb-10">
          An AI-powered assistant for smarter learning.
        </p>
        <button
          onClick={() => navigate("/chat")}
          className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-8 rounded-2xl shadow-md transition duration-300"
        >
          Go to Chat
        </button>
      </div>
    </div>
  );
};

export default Home;
