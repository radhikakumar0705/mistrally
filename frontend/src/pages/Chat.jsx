import { Menu } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Composer from "../components/chat/Composer";
import EmptyState from "../components/chat/EmptyState";
import MessageList from "../components/chat/MessageList";
import ModelPicker from "../components/chat/ModelPicker";
import Sidebar from "../components/chat/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../hooks/useChat";
import { useDocuments } from "../hooks/useDocuments";

export default function ChatPage() {
  const chat = useChat();
  const documents = useDocuments();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { currentId, selectSession } = chat;

  // Keep the URL and the open chat in sync: /chat/42 opens chat 42, and back/forward work
  useEffect(() => {
    const fromUrl = sessionId ? Number(sessionId) : null;
    if (fromUrl !== currentId) selectSession(fromUrl);
    // only react to URL changes here; the effect below handles in-app changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const previousId = useRef(currentId);
  useEffect(() => {
    if (previousId.current === currentId) return; // not on first render, or a deep link would be undone
    previousId.current = currentId;
    const target = currentId ? `/chat/${currentId}` : "/chat";
    if (window.location.pathname !== target) navigate(target, { replace: !sessionId && Boolean(currentId) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId]);

  const title = chat.currentSession?.title || "New chat";
  const isEmpty = chat.messages.length === 0 && !chat.loadingMessages;

  return (
    <div className="flex h-dvh overflow-hidden bg-zinc-950">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={chat.sessions}
        sessionsLoaded={chat.sessionsLoaded}
        currentId={chat.currentId}
        onSelect={chat.selectSession}
        onNewChat={chat.newChat}
        onRename={chat.renameSession}
        onDelete={chat.removeSession}
        documents={documents}
        user={user}
        onLogout={logout}
      />

      <main className="relative flex min-w-0 flex-1 flex-col">
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-gradient-to-b from-violet-600/[0.07] to-transparent" />

        <header className="relative z-10 flex h-16 shrink-0 items-center gap-3 border-b border-white/5 px-4 sm:px-6">
          <button type="button" onClick={() => setSidebarOpen(true)} className="icon-btn md:hidden" aria-label="Open sidebar">
            <Menu className="h-5 w-5" />
          </button>
          <h2 className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-200">{title}</h2>
          <ModelPicker
            models={chat.models}
            value={chat.activeModel}
            onChange={chat.chooseModel}
            disabled={chat.streaming}
          />
        </header>

        {chat.loadingMessages ? (
          <div className="flex flex-1 items-center justify-center">
            <span className="h-6 w-6 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
          </div>
        ) : isEmpty ? (
          <EmptyState onPick={chat.send} documentCount={documents.documents.length} />
        ) : (
          <MessageList messages={chat.messages} streaming={chat.streaming} onRegenerate={chat.regenerate} />
        )}

        <Composer
          onSend={chat.send}
          onStop={chat.stop}
          onUpload={documents.upload}
          streaming={chat.streaming}
          uploading={documents.uploading}
        />
      </main>
    </div>
  );
}
