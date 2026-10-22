import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { FlashcardDeck } from "../../api/types";

export default function FlashcardsView({ deck }: { deck: FlashcardDeck }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const card = deck.cards[index]!; // go() keeps the index within bounds

  const go = (delta: number) => {
    setFlipped(false);
    setIndex((i) => Math.min(Math.max(i + delta, 0), deck.cards.length - 1));
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === " ") {
        e.preventDefault();
        setFlipped((f) => !f);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="flex flex-col items-center">
      <div className="w-full [perspective:1200px]">
        <motion.button
          type="button"
          onClick={() => setFlipped((f) => !f)}
          animate={{ rotateY: flipped ? 180 : 0 }}
          transition={{ duration: 0.45, ease: "easeInOut" }}
          className="relative h-64 w-full [transform-style:preserve-3d]"
          aria-label={flipped ? "Show question" : "Show answer"}
        >
          <div className="absolute inset-0 flex flex-col items-center justify-center rounded-2xl border border-violet-500/30 bg-gradient-to-br from-violet-600/20 to-fuchsia-600/10 p-6 text-center [backface-visibility:hidden]">
            <span className="mb-3 text-xs uppercase tracking-wide text-violet-300">Question</span>
            <p className="text-lg font-medium text-white">{card.front}</p>
          </div>
          <div className="absolute inset-0 flex flex-col items-center justify-center rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-center [backface-visibility:hidden] [transform:rotateY(180deg)]">
            <span className="mb-3 text-xs uppercase tracking-wide text-emerald-300">Answer</span>
            <p className="text-base text-zinc-100">{card.back}</p>
          </div>
        </motion.button>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button type="button" onClick={() => go(-1)} disabled={index === 0} className="icon-btn h-10 w-10" aria-label="Previous card">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <span className="min-w-[4rem] text-center text-sm text-zinc-400">
          {index + 1} / {deck.cards.length}
        </span>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={index === deck.cards.length - 1}
          className="icon-btn h-10 w-10"
          aria-label="Next card"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
        <button type="button" onClick={() => setFlipped((f) => !f)} className="btn-secondary ml-2 py-2">
          <RotateCw className="h-4 w-4" /> Flip
        </button>
      </div>
      <p className="mt-3 text-xs text-zinc-500">Space flips · ← → move between cards</p>
    </div>
  );
}
