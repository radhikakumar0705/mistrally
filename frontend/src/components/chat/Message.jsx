import { motion } from "framer-motion";
import { CircleStop, FileText, RefreshCw, TriangleAlert } from "lucide-react";
import { memo } from "react";
import { LogoMark } from "../Logo";
import CopyButton from "./CopyButton";
import Markdown from "./Markdown";

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-2" aria-label="Mistrally is thinking">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-2 w-2 animate-bounce rounded-full bg-violet-400/80"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}

function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-zinc-500">Sources</span>
      {sources.map((source) => {
        // Older answers stored plain file names; newer ones store {document, page}
        const { document, page } = typeof source === "string" ? { document: source } : source;
        const label = page ? `${document} · p. ${page}` : document;
        return (
          <span
            key={label}
            className="inline-flex items-center gap-1 rounded-full border border-violet-500/20 bg-violet-500/10 px-2.5 py-0.5 text-xs text-violet-200"
          >
            <FileText className="h-3 w-3" />
            {label}
          </span>
        );
      })}
    </div>
  );
}

function Message({ message, isLast, streaming, onRegenerate }) {
  if (message.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md border border-violet-500/20 bg-gradient-to-br from-violet-600/30 to-fuchsia-600/20 px-4 py-2.5 text-[15px] leading-relaxed text-zinc-50">
          {message.content}
        </div>
      </motion.div>
    );
  }

  const isStreaming = message.pending && message.content;
  const showActions = !message.pending && message.content;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="group flex gap-3 sm:gap-4">
      <div className="pt-0.5">
        <LogoMark size="sm" />
      </div>
      <div className="min-w-0 flex-1">
        {message.pending && !message.content ? <TypingDots /> : null}
        {message.content ? (
          <div className="relative">
            <Markdown content={message.content} />
            {isStreaming ? (
              <span className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 animate-blink rounded-sm bg-violet-400" />
            ) : null}
          </div>
        ) : null}

        {message.error ? (
          <div className="mt-2 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{message.error}</span>
          </div>
        ) : null}

        {message.stopped ? (
          <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-zinc-500">
            <CircleStop className="h-3.5 w-3.5" /> Stopped
          </div>
        ) : null}

        <Sources sources={message.sources} />

        {showActions ? (
          <div className="mt-2 flex items-center gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
            <CopyButton getText={() => message.content} label="Copy answer" />
            {isLast && !streaming ? (
              <button type="button" onClick={onRegenerate} className="icon-btn" title="Regenerate" aria-label="Regenerate">
                <RefreshCw className="h-4 w-4" />
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}

export default memo(Message);
