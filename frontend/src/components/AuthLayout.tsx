import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import GlowBackground from "./GlowBackground";
import { LogoMark } from "./Logo";

interface Props {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export default function AuthLayout({ title, subtitle, children, footer }: Props) {
  return (
    <div className="relative flex min-h-dvh items-center justify-center px-4 py-12">
      <GlowBackground />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-sm"
      >
        <Link to="/" className="mx-auto mb-8 flex w-fit" aria-label="Mistrally home">
          <LogoMark size="lg" />
        </Link>
        <div className="glass rounded-3xl p-8 shadow-2xl shadow-black/40">
          <h1 className="text-center text-2xl font-semibold tracking-tight text-white">{title}</h1>
          <p className="mt-1.5 text-center text-sm text-zinc-400">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
        <p className="mt-6 text-center text-sm text-zinc-400">{footer}</p>
      </motion.div>
    </div>
  );
}
