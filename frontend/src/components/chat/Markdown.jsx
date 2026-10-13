import "highlight.js/styles/github-dark.css";
import { Children, memo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import CopyButton from "./CopyButton";

function CodeBlock({ children }) {
  const preRef = useRef(null);
  const code = Children.toArray(children)[0];
  const language = /language-([\w+-]+)/.exec(code?.props?.className || "")?.[1];

  return (
    <div className="not-prose group my-4 overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="flex items-center justify-between border-b border-white/5 bg-white/[0.03] py-1 pl-4 pr-1.5">
        <span className="font-mono text-xs text-zinc-400">{language || "code"}</span>
        <CopyButton getText={() => preRef.current?.innerText ?? ""} label="Copy code" />
      </div>
      <pre ref={preRef} className="scrollbar-thin overflow-x-auto p-4 font-mono text-[13px] leading-relaxed text-zinc-200">
        {children}
      </pre>
    </div>
  );
}

const components = {
  pre: CodeBlock,
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer noopener" />,
  table: ({ node: _node, ...props }) => (
    <div className="scrollbar-thin overflow-x-auto">
      <table {...props} />
    </div>
  ),
};

const rehypePlugins = [[rehypeHighlight, { detect: true }]];
const remarkPlugins = [remarkGfm];

function Markdown({ content }) {
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
