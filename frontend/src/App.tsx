import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import ProtectedRoute, { PageSpinner } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import AuthCallback from "./pages/AuthCallback";
import Home from "./pages/Home";
import Login from "./pages/Login";
import NotFound from "./pages/Notfound";
import Signup from "./pages/Signup";

// The chat page pulls in Markdown + syntax highlighting; load it only when needed
const Chat = lazy(() => import("./pages/Chat"));


export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="/chat/:sessionId?"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSpinner />}>
                  <Chat />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
      <Toaster theme="dark" position="top-center" richColors closeButton />
    </AuthProvider>
  );
}
