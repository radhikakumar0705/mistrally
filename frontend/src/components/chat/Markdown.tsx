import "highlight.js/styles/github-dark.css";
import { Loader2, Play, X } from "lucide-react";
import { Children, isValidElement, memo, useRef, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import type { PluggableList } from "unified";
import { errorMessage } from "../../api/axiosClient";
import { runCode } from "../../api/study";
import type { RunResult } from "../../api/types";
import { useFeatures } from "../../context/FeaturesContext";
import CopyButton from "./CopyButton";

const RUNNABLE = new Set(["python", "py", "python3"]);

type RunOutcome = RunResult | { error: string };

function RunOutput({ result, onClose }: { result: RunOutcome; onClose: () => void }) {
  return (
    <div className="border-t border-white/5 bg-black/30 font-mono text-[13px]">
      <div className="flex items-center justify-between px-4 py-1.5 text-xs text-zinc-500">
        <span>
          {"error" in result
            ? "Could not run"
            : `${result.timed_out ? "Timed out" : `Exit code ${result.exit_code}`} · ${result.duration_ms ?? 0} ms`}
        </span>
        <button type="button" onClick={onClose} className="icon-btn h-6 w-6" aria-label="Close output">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <pre className="scrollbar-thin max-h-64 overflow-auto whitespace-pre-wrap px-4 pb-3" aria-label="Program output">
        {"error" in result ? (
          <span className="text-red-300">{result.error}</span>
        ) : (
          <>
            {result.stdout ? <span className="text-zinc-200">{result.stdout}</span> : null}
            {result.stderr ? <span className="text-red-300">{result.stderr}</span> : null}
            {!result.stdout && !result.stderr ? <span className="text-zinc-500">(no output)</span> : null}
          </>
        )}
      </pre>
    </div>
  );
}

function codeLanguage(children: ReactNode): string | undefined {
  const code = Children.toArray(children)[0];
  if (!isValidElement<{ className?: string }>(code)) return undefined;
  return /language-([\w+-]+)/.exec(code.props.className || "")?.[1];
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const preRef = useRef<HTMLPreElement>(null);
  const { sandbox } = useFeatures();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunOutcome | null>(null);
  const language = codeLanguage(children);
  const canRun = sandbox && RUNNABLE.has(language?.toLowerCase() ?? "");
  const codeText = () => preRef.current?.textContent ?? "";

  const run = async () => {
    setRunning(true);
    try {
      setResult(await runCode(codeText()));
    } catch (error) {
      setResult({ error: errorMessage(error, "The code runner is unavailable") });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="not-prose group my-4 overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="flex items-center justify-between border-b border-white/5 bg-white/[0.03] py-1 pl-4 pr-1.5">
        <span className="font-mono text-xs text-zinc-400">{language || "code"}</span>
        <div className="flex items-center gap-1">
          {canRun ? (
            <button
              type="button"
              onClick={run}
              disabled={running}
              className="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/10 disabled:opacity-60"
              aria-label="Run code"
            >
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Run
            </button>
          ) : null}
          <CopyButton getText={codeText} label="Copy code" />
        </div>
      </div>
      <pre ref={preRef} className="scrollbar-thin overflow-x-auto p-4 font-mono text-[13px] leading-relaxed text-zinc-200">
        {children}
      </pre>
      {result ? <RunOutput result={result} onClose={() => setResult(null)} /> : null}
    </div>
  );
}

const components: Components = {
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer noopener" />,
  table: ({ node: _node, ...props }) => (
    <div className="scrollbar-thin overflow-x-auto">
      <table {...props} />
    </div>
  ),
};

const rehypePlugins: PluggableList = [[rehypeHighlight, { detect: true }]];
const remarkPlugins: PluggableList = [remarkGfm];

function Markdown({ content }: { content: string }) {
  return (
    <div
      className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:my-0 prose-code:rounded-md prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[0.85em] prose-code:font-normal prose-code:text-fuchsia-200 prose-a:text-violet-300 prose-strong:text-white prose-headings:text-white prose-li:marker:text-zinc-500"
    >
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default memo(Markdown);
