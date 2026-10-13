import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import Home from "./pages/Home";
import Login from "./pages/Login";
import NotFound from "./pages/Notfound";
import Signup from "./pages/Signup";

// The chat page pulls in Markdown + syntax highlighting; load it only when needed
const Chat = lazy(() => import("./pages/Chat"));

const PageSpinner = () => (
  <div className="flex h-dvh items-center justify-center">
    <span className="h-6 w-6 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
  </div>
);

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
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
