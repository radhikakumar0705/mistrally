import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, GraduationCap, Layers, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { errorMessage } from "../../api/axiosClient";
import { generateStudy } from "../../api/study";
import FlashcardsView from "./FlashcardsView";
import QuizView from "./QuizView";

const KINDS = [
  { id: "quiz", label: "Quiz", icon: GraduationCap },
  { id: "flashcards", label: "Flashcards", icon: Layers },
];

export default function StudyDialog({ open, onClose, documents, model }) {
  const readyDocs = documents.filter((d) => d.status === "ready");
  const [kind, setKind] = useState("quiz");
  const [source, setSource] = useState(readyDocs.length ? "document" : "topic");
  const [documentId, setDocumentId] = useState(readyDocs[0]?.id || "");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // The dialog mounts before documents load, so pick a sensible default each time it opens
  const firstReadyId = readyDocs[0]?.id || "";
  useEffect(() => {
    if (!open) return;
    setDocumentId((current) => current || firstReadyId);
    if (firstReadyId) setSource((current) => (current === "topic" && !topic ? "document" : current));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, firstReadyId]);

  const generate = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const options = { count, difficulty, model };
      if (source === "document") options.document_id = documentId;
      else options.topic = topic;
      setResult(await generateStudy(kind, options));
    } catch (err) {
      setError(errorMessage(err, "Could not generate study material"));
    } finally {
      setLoading(false);
    }
  };

  const canGenerate = source === "document" ? Boolean(documentId) : topic.trim().length > 1;

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Study tools"
            initial={{ y: 24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 24, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="glass flex max-h-[92dvh] w-full max-w-2xl flex-col rounded-t-3xl shadow-2xl shadow-black/60 sm:rounded-3xl"
          >
            <div className="flex items-center gap-3 border-b border-white/5 px-5 py-4">
              {result ? (
                <button type="button" onClick={() => setResult(null)} className="icon-btn" aria-label="Back">
                  <ArrowLeft className="h-5 w-5" />
                </button>
              ) : (
                <Sparkles className="h-5 w-5 text-violet-300" />
              )}
              <h2 className="min-w-0 flex-1 truncate font-semibold text-white">
                {result ? result.title : "Study mode"}
              </h2>
              <button type="button" onClick={onClose} className="icon-btn" aria-label="Close study mode">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="scrollbar-thin overflow-y-auto p-5">
              {result ? (
                result.kind === "quiz" ? (
                  <QuizView quiz={result} />
                ) : (
                  <FlashcardsView deck={result} />
                )
              ) : (
                <form onSubmit={generate} className="space-y-5">
                  <div className="grid grid-cols-2 gap-2 rounded-xl bg-white/5 p-1">
                    {KINDS.map(({ id, label, icon: Icon }) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setKind(id)}
                        aria-pressed={kind === id}
                        className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition ${
                          kind === id ? "bg-violet-600 text-white shadow" : "text-zinc-400 hover:text-zinc-100"
                        }`}
                      >
                        <Icon className="h-4 w-4" /> {label}
                      </button>
                    ))}
                  </div>

                  <fieldset className="space-y-3">
                    <legend className="mb-2 text-sm font-medium text-zinc-300">Study from</legend>
                    <label className="flex items-center gap-3 text-sm text-zinc-300">
                      <input
                        type="radio"
                        name="source"
                        checked={source === "document"}
                        onChange={() => setSource("document")}
                        disabled={!readyDocs.length}
                        className="accent-violet-500"
                      />
                      One of my documents
                    </label>
                    {source === "document" ? (
                      <select
                        value={documentId}
                        onChange={(e) => setDocumentId(e.target.value)}
                        className="input"
                        aria-label="Document"
                      >
                        {readyDocs.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.filename}
                          </option>
                        ))}
                      </select>
                    ) : null}
                    <label className="flex items-center gap-3 text-sm text-zinc-300">
                      <input
                        type="radio"
                        name="source"
                        checked={source === "topic"}
                        onChange={() => setSource("topic")}
                        className="accent-violet-500"
                      />
                      A topic
                    </label>
                    {source === "topic" ? (
                      <input
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g. Python decorators, SQL joins, Big-O"
                        className="input"
                        aria-label="Topic"
                        maxLength={200}
                        autoFocus
                      />
                    ) : null}
                    {!readyDocs.length ? (
                      <p className="text-xs text-zinc-500">Upload a document to study from your own notes.</p>
                    ) : null}
                  </fieldset>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="text-sm text-zinc-300">
                      {kind === "quiz" ? "Questions" : "Cards"}
                      <select value={count} onChange={(e) => setCount(Number(e.target.value))} className="input mt-1.5">
                        {[3, 5, 8, 10].map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </label>
                    {kind === "quiz" ? (
                      <label className="text-sm text-zinc-300">
                        Difficulty
                        <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="input mt-1.5">
                          <option value="easy">Easy</option>
                          <option value="medium">Medium</option>
                          <option value="hard">Hard</option>
                        </select>
                      </label>
                    ) : null}
                  </div>

                  {error ? (
                    <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                      {error}
                    </p>
                  ) : null}

                  <button type="submit" disabled={!canGenerate || loading} className="btn-primary w-full py-3">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {loading ? "Generating…" : `Generate ${kind === "quiz" ? "quiz" : "flashcards"}`}
                  </button>
                </form>
              )}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
