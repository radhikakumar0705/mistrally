import { motion } from "framer-motion";
import { ArrowRight, Cpu, FileText, Layers, ShieldCheck, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import GlowBackground from "../components/GlowBackground";
import { LogoMark } from "../components/Logo";
import NavBar from "../components/NavBar";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  {
    icon: Zap,
    title: "Streaming answers",
    text: "Replies appear word by word as the model writes them. Stop or regenerate any time.",
  },
  {
    icon: FileText,
    title: "Chat with your notes",
    text: "Upload PDFs or text files. sockRat finds the relevant passages and cites them.",
  },
  {
    icon: ShieldCheck,
    title: "Private by design",
    text: "Runs on local models through Ollama. Your questions never leave your machine.",
  },
  {
    icon: Cpu,
    title: "Pick your model",
    text: "Switch between Mistral, Llama and any other model you have installed, per chat.",
  },
];

function PreviewCard() {
  return (
    <div className="glass mx-auto w-full max-w-2xl rounded-3xl p-2 shadow-2xl shadow-violet-950/40">
      <div className="flex items-center gap-1.5 px-3 py-2">
        <span className="h-3 w-3 rounded-full bg-zinc-700" />
        <span className="h-3 w-3 rounded-full bg-zinc-700" />
        <span className="h-3 w-3 rounded-full bg-zinc-700" />
      </div>
      <div className="space-y-4 rounded-2xl bg-zinc-950/80 p-5 text-left text-sm">
        <div className="flex justify-end">
          <div className="rounded-2xl rounded-br-md border border-violet-500/20 bg-gradient-to-br from-violet-600/30 to-fuchsia-600/20 px-4 py-2.5 text-zinc-50">
            How do I reverse a list in Python?
          </div>
        </div>
        <div className="flex gap-3">
          <LogoMark size="sm" />
          <div className="min-w-0 flex-1 space-y-3 text-zinc-300">
            <p>
              Use slicing for a reversed <em>copy</em>, or <code className="rounded bg-white/10 px-1.5 py-0.5 text-fuchsia-200">reverse()</code> to
              change the list in place:
            </p>
            <div className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
              <div className="border-b border-white/5 bg-white/[0.03] px-4 py-1.5 font-mono text-xs text-zinc-400">python</div>
              <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-relaxed">
                <span className="text-zinc-200">nums = [</span>
                <span className="text-sky-300">1, 2, 3</span>
                <span className="text-zinc-200">]{"\n"}copy = nums[::-</span>
                <span className="text-sky-300">1</span>
                <span className="text-zinc-200">]   </span>
                <span className="text-zinc-500"># [3, 2, 1]</span>
                <span className="text-zinc-200">{"\n"}nums.</span>
                <span className="text-violet-300">reverse</span>
                <span className="text-zinc-200">()   </span>
                <span className="text-zinc-500"># nums is now [3, 2, 1]</span>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const { isLoggedIn } = useAuth();

  return (
    <div className="relative min-h-dvh">
      <GlowBackground />
      <NavBar />

      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        <section className="flex flex-col items-center pb-16 pt-16 text-center sm:pt-24">
          <motion.span
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-200"
          >
            <Layers className="h-3.5 w-3.5" /> Local LLMs · RAG · Streaming
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-6xl"
          >
            Your private AI tutor <span className="text-gradient">for learning to code</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-5 max-w-xl text-lg text-zinc-400"
          >
            sockRat explains concepts, debugs your code and answers questions about your own notes, all on
            models running on your machine.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mt-8 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to={isLoggedIn ? "/chat" : "/signup"} className="btn-primary px-6 py-3 text-base">
              {isLoggedIn ? "Open chat" : "Start for free"} <ArrowRight className="h-4 w-4" />
            </Link>
            {!isLoggedIn ? (
              <Link to="/login" className="btn-secondary px-6 py-3 text-base">
                I have an account
              </Link>
            ) : null}
          </motion.div>
        </section>

        <motion.section initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <PreviewCard />
        </motion.section>

        <section className="grid gap-4 py-20 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-violet-500/30 hover:bg-violet-500/[0.04]"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
                <Icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 font-medium text-white">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{text}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-white/5 py-8 text-center text-sm text-zinc-500">
        Built with React, Flask, Ollama and ChromaDB.
      </footer>
    </div>
  );
}
