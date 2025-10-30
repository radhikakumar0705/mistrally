// src/pages/NotFoundPage.jsx
import { Link } from "react-router-dom";

const NotFound = () => (
  <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
    <h1 className="text-5xl font-bold mb-4">404</h1>
    <p className="text-lg mb-4">Page not found</p>
    <Link to="/" className="text-blue-500">Go Home</Link>
  </div>
);

export default NotFound;
