import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";

export default function NavBar() {
  const { isLoggedIn } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b border-white/5 bg-zinc-950/70 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/" aria-label="sockRat home">
          <Logo />
        </Link>
        <div className="flex items-center gap-2">
          {isLoggedIn ? (
            <Link to="/chat" className="btn-primary">
              Open chat
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn-secondary border-transparent bg-transparent">
                Log in
              </Link>
              <Link to="/signup" className="btn-primary">
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
