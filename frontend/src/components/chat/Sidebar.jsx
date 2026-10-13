import {
  AlertCircle,
  Check,
  ChevronDown,
  FileText,
  Loader2,
  LogOut,
  MessageSquare,
  Pencil,
  Plus,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import authApi from "../../api/auth";
import Logo from "../Logo";
import { groupByDate } from "../../lib/dates";

function SessionItem({ session, active, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [title, setTitle] = useState(session.title);

  const save = () => {
    setEditing(false);
    const next = title.trim();
    if (next && next !== session.title) onRename(session.id, next);
    else setTitle(session.title);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1.5">
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") {
              setTitle(session.title);
              setEditing(false);
            }
          }}
          aria-label="Chat title"
          className="min-w-0 flex-1 bg-transparent text-sm text-zinc-100 outline-none"
        />
      </div>
    );
  }

  return (
    <div
      className={`group relative flex items-center rounded-lg transition ${
        active ? "bg-white/10 text-white" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
      }`}
    >
      <button
        type="button"
        onClick={() => onSelect(session.id)}
        className="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2 text-left text-sm"
        aria-current={active ? "page" : undefined}
      >
        <MessageSquare className={`h-4 w-4 shrink-0 ${active ? "text-violet-300" : "text-zinc-500"}`} />
        <span className="truncate">{session.title}</span>
      </button>

      {confirming ? (
        <div className="flex shrink-0 items-center pr-1">
          <button
            type="button"
            onClick={() => onDelete(session.id)}
            className="icon-btn h-7 w-7 text-red-400 hover:text-red-300"
            aria-label="Confirm delete"
            title="Delete"
          >
            <Check className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="icon-btn h-7 w-7"
            aria-label="Cancel delete"
            title="Cancel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="flex shrink-0 items-center pr-1 opacity-100 transition md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="icon-btn h-7 w-7"
            aria-label="Rename chat"
            title="Rename"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="icon-btn h-7 w-7 hover:text-red-400"
            aria-label="Delete chat"
            title="Delete"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

function DocumentsPanel({ documents, uploading, onUpload, onRemove }) {
  const [open, setOpen] = useState(true);
  const fileRef = useRef(null);

  return (
    <div className="border-t border-white/5 px-3 py-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500 hover:text-zinc-300"
          aria-expanded={open}
        >
          <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "" : "-rotate-90"}`} />
          Documents
          <span className="rounded-full bg-white/10 px-1.5 text-[10px] text-zinc-300">{documents.length}</span>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="icon-btn h-7 w-7"
          title="Upload a PDF, TXT or Markdown file"
          aria-label="Upload document"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
        </button>
      </div>

      {open ? (
        <ul className="scrollbar-thin mt-2 max-h-40 space-y-0.5 overflow-y-auto">
          {documents.length === 0 ? (
            <li className="px-2 py-1.5 text-xs leading-relaxed text-zinc-500">
              Upload notes or docs and Mistrally will use them in its answers.
            </li>
          ) : (
            documents.map((doc) => (
              <li key={doc.id} className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-zinc-300 hover:bg-white/5">
                {doc.status === "failed" ? (
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                ) : doc.status === "ready" ? (
                  <FileText className="h-4 w-4 shrink-0 text-fuchsia-300" />
                ) : (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-violet-300" />
                )}
                <div className="min-w-0 flex-1">
                  <span className="block truncate" title={doc.error || doc.filename}>
                    {doc.filename}
                  </span>
                  {doc.status === "queued" || doc.status === "processing" ? (
                    <div
                      className="mt-1 h-1 overflow-hidden rounded-full bg-white/10"
                      role="progressbar"
                      aria-valuenow={doc.progress}
                      aria-label={`Processing ${doc.filename}`}
                    >
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-500"
                        style={{ width: `${Math.max(doc.progress, doc.status === "queued" ? 4 : 10)}%` }}
                      />
                    </div>
                  ) : doc.status === "failed" ? (
                    <span className="block truncate text-xs text-red-300">{doc.error || "Failed"}</span>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(doc)}
                  className="icon-btn h-6 w-6 opacity-100 hover:text-red-400 md:opacity-0 md:group-hover:opacity-100"
                  aria-label={`Remove ${doc.filename}`}
                  title="Remove"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}

export default function Sidebar({
  open,
  onClose,
  sessions,
  sessionsLoaded,
  currentId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  documents,
  user,
  googleEnabled,
  onLogout,
}) {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q ? sessions.filter((s) => s.title.toLowerCase().includes(q)) : sessions;
    return groupByDate(filtered, (s) => s.updated_at || s.created_at);
  }, [sessions, query]);

  const select = (id) => {
    onSelect(id);
    onClose();
  };

  return (
    <>
      {/* Mobile overlay */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity md:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-white/5 bg-zinc-900/95 backdrop-blur-xl transition-transform duration-300 md:static md:translate-x-0 md:bg-zinc-900/40 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Chats"
      >
        <div className="flex h-16 items-center justify-between px-4">
          <Logo size="sm" />
          <button type="button" onClick={onClose} className="icon-btn md:hidden" aria-label="Close sidebar">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-2 px-3">
          <button
            type="button"
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="btn-primary w-full"
          >
            <Plus className="h-4 w-4" /> New chat
          </button>
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chats"
              aria-label="Search chats"
              className="input rounded-lg py-2 pl-9 text-sm"
            />
          </label>
        </div>

        <nav className="scrollbar-thin mt-3 min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {!sessionsLoaded ? (
            <div className="space-y-2 px-1 pt-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-8 animate-pulse rounded-lg bg-white/5" />
              ))}
            </div>
          ) : groups.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-zinc-500">
              {query ? "No chats match your search." : "No chats yet. Say hello!"}
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-3">
                <h3 className="px-3 pb-1 pt-2 text-xs font-medium text-zinc-500">{group.label}</h3>
                <div className="space-y-0.5">
                  {group.items.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      active={session.id === currentId}
                      onSelect={select}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </nav>

        <DocumentsPanel
          documents={documents.documents}
          uploading={documents.uploading}
          onUpload={documents.upload}
          onRemove={documents.remove}
        />

        <div className="flex items-center gap-3 border-t border-white/5 px-4 py-3">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt=""
              referrerPolicy="no-referrer"
              className="h-8 w-8 shrink-0 rounded-full object-cover ring-1 ring-white/10"
            />
          ) : (
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-sm font-semibold uppercase text-white">
              {user?.username?.[0] || "?"}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-zinc-100">{user?.name || user?.username || "Signed in"}</p>
            {googleEnabled && user && !user.google_linked ? (
              <a href={authApi.googleLinkUrl()} className="text-xs text-violet-300 hover:text-violet-200">
                Connect Google
              </a>
            ) : user?.email ? (
              <p className="truncate text-xs text-zinc-500">{user.email}</p>
            ) : null}
          </div>
          <button type="button" onClick={onLogout} className="icon-btn" title="Log out" aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>
    </>
  );
}
