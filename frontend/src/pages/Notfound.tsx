import { Link } from "react-router-dom";
import GlowBackground from "../components/GlowBackground";

export default function NotFound() {
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center px-4 text-center">
      <GlowBackground />
      <p className="text-gradient text-7xl font-bold tracking-tight">404</p>
      <h1 className="mt-4 text-xl font-semibold text-white">Page not found</h1>
      <p className="mt-2 text-zinc-400">The page you&apos;re looking for doesn&apos;t exist.</p>
      <Link to="/" className="btn-primary mt-8">
        Go home
      </Link>
    </div>
  );
}
