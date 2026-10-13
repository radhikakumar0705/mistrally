import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const PageSpinner = () => (
  <div className="flex h-dvh items-center justify-center">
    <span className="h-6 w-6 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
  </div>
);

export default function ProtectedRoute({ children }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <PageSpinner />;
  return status === "authenticated" ? children : <Navigate to="/login" replace state={{ from: location }} />;
}
