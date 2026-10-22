import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { errorMessage } from "../api/axiosClient";
import {
  createSession,
  deleteSession as apiDeleteSession,
  getChatSessions,
  getModels,
  getSessionMessages,
  streamMessage,
  streamRegenerate,
  updateSession,
  type StreamOptions,
} from "../api/chat";
import type { ChatMessage, ChatSession, Source } from "../api/types";

/** A message as shown in the UI: saved history, or a local message that is still streaming. */
export interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: (Source | string)[];
  pending?: boolean;
  error?: string;
  stopped?: boolean;
}

let lastLocalId = 0;
const localId = () => `local-${++lastLocalId}`;

const toMessages = (history: ChatMessage[]): UiMessage[] =>
  history.flatMap((h): UiMessage[] => [
    { id: `u-${h.id}`, role: "user", content: h.user_message },
    { id: `a-${h.id}`, role: "assistant", content: h.bot_response, sources: h.sources || [] },
  ]);

const isAbort = (error: unknown) =>
  typeof error === "object" && error !== null && (error as { name?: string }).name === "AbortError";

/**
 * All chat state for the chat page: the session list, the open conversation,
 * the model picker, and streaming replies (with stop and regenerate).
 */
export function useChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [models, setModels] = useState<{ models: string[]; default: string | null }>({ models: [], default: null });
  const [draftModel, setDraftModel] = useState<string | null>(null); // model chosen before the first message

  const currentIdRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);

  const replaceSession = useCallback(
    (session: ChatSession) => setSessions((prev) => prev.map((s) => (s.id === session.id ? session : s))),
    []
  );
  // Sessions are ordered by latest activity, so an updated session moves to the top
  const bumpSession = useCallback(
    (session: ChatSession) => setSessions((prev) => [session, ...prev.filter((s) => s.id !== session.id)]),
    []
  );

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await getChatSessions());
    } catch (error) {
      toast.error(errorMessage(error, "Could not load your chats"));
    } finally {
      setSessionsLoaded(true);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
    getModels()
      .then(setModels)
      .catch(() => {}); // the picker falls back to the server default when the model is unreachable
    return () => abortRef.current?.abort();
  }, [refreshSessions]);

  const selectSession = useCallback(async (id: number | null) => {
    abortRef.current?.abort();
    currentIdRef.current = id;
    setCurrentId(id);
    setMessages([]);
    if (id == null) return;

    setLoadingMessages(true);
    try {
      const history = await getSessionMessages(id);
      if (currentIdRef.current === id) setMessages(toMessages(history));
    } catch (error) {
      if (currentIdRef.current === id) toast.error(errorMessage(error, "Could not load this chat"));
    } finally {
      if (currentIdRef.current === id) setLoadingMessages(false);
    }
  }, []);

  const newChat = useCallback(() => {
    setDraftModel(null);
    selectSession(null);
  }, [selectSession]);

  const runStream = useCallback(
    async (assistantId: string, start: (options: StreamOptions) => Promise<void>) => {
      const controller = new AbortController();
      abortRef.current = controller;
      const patch = (update: (m: UiMessage) => Partial<UiMessage>) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, ...update(m) } : m)));

      try {
        await start({
          signal: controller.signal,
          onEvent: (event) => {
            switch (event.type) {
              case "start":
                patch(() => ({ sources: event.sources }));
                break;
              case "token":
                patch((m) => ({ content: m.content + event.content }));
                break;
              case "error":
                patch(() => ({ error: event.error }));
                break;
              case "done":
                bumpSession(event.session);
                break;
            }
          },
        });
      } catch (error) {
        if (isAbort(error)) {
          patch(() => ({ stopped: true }));
          refreshSessions(); // the server saved the partial answer and bumped the session
        } else {
          patch(() => ({ error: errorMessage(error, "The answer was interrupted") }));
        }
      } finally {
        patch(() => ({ pending: false }));
        if (abortRef.current === controller) abortRef.current = null;
        streamingRef.current = false;
        setStreaming(false);
      }
    },
    [bumpSession, refreshSessions]
  );

  const send = useCallback(
    async (text: string) => {
      if (streamingRef.current) return;
      streamingRef.current = true;
      setStreaming(true);

      const assistantId = localId();
      setMessages((prev) => [
        ...prev,
        { id: localId(), role: "user", content: text },
        { id: assistantId, role: "assistant", content: "", sources: [], pending: true },
      ]);

      let sessionId = currentIdRef.current;
      if (sessionId == null) {
        // Chats are created on the first message, so empty chats never pile up
        try {
          const session = await createSession({ model: draftModel });
          sessionId = session.id;
          currentIdRef.current = session.id;
          setCurrentId(session.id);
          bumpSession(session);
        } catch (error) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, pending: false, error: errorMessage(error, "Could not start a chat") } : m
            )
          );
          streamingRef.current = false;
          setStreaming(false);
          return;
        }
      }

      const id = sessionId;
      await runStream(assistantId, (options) => streamMessage(id, text, options));
    },
    [draftModel, bumpSession, runStream]
  );

  const regenerate = useCallback(async () => {
    const sessionId = currentIdRef.current;
    if (streamingRef.current || sessionId == null) return;
    streamingRef.current = true;
    setStreaming(true);

    const assistantId = localId();
    setMessages((prev) => [
      ...prev.slice(0, -1),
      { id: assistantId, role: "assistant", content: "", sources: [], pending: true },
    ]);
    await runStream(assistantId, (options) => streamRegenerate(sessionId, options));
  }, [runStream]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const removeSession = useCallback(
    async (id: number) => {
      try {
        await apiDeleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (currentIdRef.current === id) newChat();
        toast.success("Chat deleted");
      } catch (error) {
        toast.error(errorMessage(error, "Could not delete that chat"));
      }
    },
    [newChat]
  );

  const renameSession = useCallback(
    async (id: number, title: string) => {
      try {
        replaceSession(await updateSession(id, { title }));
      } catch (error) {
        toast.error(errorMessage(error, "Could not rename that chat"));
      }
    },
    [replaceSession]
  );

  const currentSession = sessions.find((s) => s.id === currentId) || null;
  const activeModel = (currentSession ? currentSession.model : draftModel) || models.default;

  const chooseModel = useCallback(
    async (model: string) => {
      const value = model === models.default ? null : model;
      if (currentIdRef.current == null) {
        setDraftModel(value);
        return;
      }
      try {
        replaceSession(await updateSession(currentIdRef.current, { model: value }));
      } catch (error) {
        toast.error(errorMessage(error, "Could not switch models"));
      }
    },
    [models.default, replaceSession]
  );

  return {
    sessions,
    sessionsLoaded,
    currentId,
    currentSession,
    messages,
    loadingMessages,
    streaming,
    models: models.models,
    activeModel,
    selectSession,
    newChat,
    send,
    stop,
    regenerate,
    removeSession,
    renameSession,
    chooseModel,
  };
}

export type ChatState = ReturnType<typeof useChat>;
