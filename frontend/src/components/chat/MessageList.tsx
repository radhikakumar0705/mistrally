import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { UiMessage } from "../../hooks/useChat";
import Message from "./Message";

const NEAR_BOTTOM_PX = 120;

interface Props {
  messages: UiMessage[];
  streaming: boolean;
  onRegenerate: () => void;
}

export default function MessageList({ messages, streaming, onRegenerate }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const el = containerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  // Follow the stream while the user is at the bottom, but don't yank them back if they scrolled up to read
  useEffect(() => {
    if (stickToBottom.current) scrollToBottom();
  }, [messages, scrollToBottom]);

  const onScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
    stickToBottom.current = nearBottom;
    setShowJump(!nearBottom);
  };

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={containerRef} onScroll={onScroll} className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-8 pt-6 sm:px-6">
          {messages.map((message, index) => (
            <Message
              key={message.id}
              message={message}
              isLast={index === messages.length - 1}
              streaming={streaming}
              onRegenerate={onRegenerate}
            />
          ))}
        </div>
      </div>
      {showJump ? (
        <button
          type="button"
          onClick={() => scrollToBottom("smooth")}
          className="glass absolute bottom-4 left-1/2 inline-flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full text-zinc-300 shadow-xl transition hover:text-white"
          aria-label="Scroll to latest message"
        >
          <ArrowDown className="h-4 w-4" />
        </button>
      ) : null}
    </div>
  );
}
