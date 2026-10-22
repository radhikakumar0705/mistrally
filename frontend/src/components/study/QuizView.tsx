import { CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";
import type { Quiz } from "../../api/types";

export default function QuizView({ quiz }: { quiz: Quiz }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const answered = Object.keys(answers).length;
  const score = quiz.questions.filter((q, i) => answers[i] === q.answer_index).length;

  return (
    <div className="space-y-4">
      {quiz.questions.map((q, i) => {
        const chosen = answers[i];
        const done = chosen !== undefined;
        return (
          <div key={i} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="font-medium text-zinc-100">
              <span className="mr-2 text-violet-300">{i + 1}.</span>
              {q.question}
            </p>
            <div className="mt-3 grid gap-2">
              {q.options.map((option, j) => {
                const isCorrect = j === q.answer_index;
                const state = !done ? "idle" : isCorrect ? "correct" : j === chosen ? "wrong" : "dim";
                const styles = {
                  idle: "border-white/10 hover:border-violet-500/50 hover:bg-violet-500/10",
                  correct: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
                  wrong: "border-red-500/50 bg-red-500/10 text-red-100",
                  dim: "border-white/5 text-zinc-500",
                };
                return (
                  <button
                    key={j}
                    type="button"
                    disabled={done}
                    onClick={() => setAnswers((prev) => ({ ...prev, [i]: j }))}
                    className={`flex items-center justify-between gap-3 rounded-xl border px-3 py-2 text-left text-sm transition ${styles[state]}`}
                  >
                    <span>{option}</span>
                    {state === "correct" ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" /> : null}
                    {state === "wrong" ? <XCircle className="h-4 w-4 shrink-0 text-red-400" /> : null}
                  </button>
                );
              })}
            </div>
            {done ? <p className="mt-3 text-sm text-zinc-400">{q.explanation}</p> : null}
          </div>
        );
      })}

      <div className="sticky bottom-0 rounded-xl border border-white/10 bg-zinc-900/95 px-4 py-3 text-sm backdrop-blur">
        {answered < quiz.questions.length ? (
          <span className="text-zinc-400">
            Answered {answered} of {quiz.questions.length}
          </span>
        ) : (
          <span className="font-medium text-white">
            You scored {score}/{quiz.questions.length}
            {score === quiz.questions.length ? " 🎉" : ""}
          </span>
        )}
      </div>
    </div>
  );
}
