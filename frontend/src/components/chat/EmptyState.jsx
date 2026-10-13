import { motion } from "framer-motion";
import { Braces, Bug, GraduationCap, Lightbulb } from "lucide-react";
import { LogoMark } from "../Logo";

const SUGGESTIONS = [
  {
    icon: GraduationCap,
    title: "Explain a concept",
    prompt: "Explain recursion with a simple Python example, then show a common mistake.",
  },
  {
    icon: Bug,
    title: "Debug my code",
    prompt: "Why does `for i in range(len(items)): items.remove(items[i])` crash in Python?",
  },
  {
    icon: Braces,
    title: "Compare approaches",
    prompt: "When should I use a dictionary instead of a list? Give examples in JavaScript.",
  },
  {
    icon: Lightbulb,
    title: "Quiz me",
    prompt: "Give me 3 short quiz questions about SQL joins, then wait for my answers.",
  },
];

export default function EmptyState({ onPick, documentCount }) {
  return (
    <div className="scrollbar-thin flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex w-full max-w-2xl flex-col items-center text-center"
      >
        <div className="animate-float">
          <LogoMark size="lg" />
        </div>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight sm:text-4xl">
          How can I help you <span className="text-gradient">learn today?</span>
        </h1>
        <p className="mt-3 max-w-md text-zinc-400">
          Ask about code, concepts or errors.
          {documentCount > 0
            ? ` I'll also search your ${documentCount} uploaded document${documentCount === 1 ? "" : "s"}.`
            : " Attach a PDF or TXT with the paperclip to chat about your own notes."}
        </p>

        <div className="mt-10 grid w-full gap-3 sm:grid-cols-2">
          {SUGGESTIONS.map(({ icon: Icon, title, prompt }, i) => (
            <motion.button
              key={title}
              type="button"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              onClick={() => onPick(prompt)}
              className="group rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:border-violet-500/40 hover:bg-violet-500/[0.06]"
            >
              <div className="flex items-center gap-2 text-sm font-medium text-zinc-100">
                <Icon className="h-4 w-4 text-violet-300" />
                {title}
              </div>
              <p className="mt-1.5 line-clamp-2 text-sm text-zinc-400 group-hover:text-zinc-300">{prompt}</p>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
