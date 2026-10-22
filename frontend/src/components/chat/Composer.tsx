import { ArrowUp, Loader2, Paperclip, Square } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";

const MAX_HEIGHT_PX = 200;

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  onUpload: (file: File) => void;
  streaming: boolean;
  uploading: boolean;
}

export default function Composer({ onSend, onStop, onUpload, streaming, uploading }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Grow with the content up to MAX_HEIGHT_PX, then scroll
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT_PX ? "auto" : "hidden";
  }, [text]);

  useEffect(() => {
    if (!streaming) textareaRef.current?.focus();
  }, [streaming]);

  const submit = () => {
    const message = text.trim();
    if (!message || streaming) return;
    onSend(message);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = "";
  };

  return (
    <div className="bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent px-4 pb-4 pt-2 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <div className="glass flex items-end gap-2 rounded-2xl p-2 shadow-2xl shadow-black/40 transition focus-within:border-violet-500/40 focus-within:ring-4 focus-within:ring-violet-500/10">
          <input ref={fileRef} type="file" accept=".pdf,.txt,.md" onChange={onFile} className="hidden" />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="icon-btn h-10 w-10 rounded-xl"
            title="Add a PDF, TXT or Markdown document for sockRat to use"
            aria-label="Upload document"
          >
            {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask sockRat anything…"
            aria-label="Message"
            className="scrollbar-thin max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] leading-relaxed text-zinc-100 outline-none placeholder:text-zinc-500 focus-visible:ring-0 focus-visible:ring-offset-0"
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-zinc-900 transition hover:bg-zinc-200"
              title="Stop generating"
              aria-label="Stop generating"
            >
              <Square className="h-4 w-4 fill-current" />
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!text.trim()}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white shadow-lg shadow-violet-900/40 transition hover:from-violet-500 hover:to-fuchsia-500 disabled:cursor-not-allowed disabled:from-zinc-800 disabled:to-zinc-800 disabled:text-zinc-500 disabled:shadow-none"
              title="Send"
              aria-label="Send message"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-xs text-zinc-500">
          <kbd className="font-sans">Enter</kbd> to send · <kbd className="font-sans">Shift + Enter</kbd> for a new
          line · sockRat runs on local models and can make mistakes.
        </p>
      </div>
    </div>
  );
}
