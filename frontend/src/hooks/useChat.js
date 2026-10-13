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
} from "../api/chat";

let lastLocalId = 0;
const localId = () => `local-${++lastLocalId}`;

const toMessages = (history) =>
  history.flatMap((h) => [
    { id: `u-${h.id}`, role: "user", content: h.user_message },
    { id: `a-${h.id}`, role: "assistant", content: h.bot_response, sources: h.sources || [] },
  ]);

/**
 * All chat state for the chat page: the session list, the open conversation,
 * the model picker, and streaming replies (with stop and regenerate).
 */
export function useChat() {
  const [sessions, setSessions] = useState([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [models, setModels] = useState({ models: [], default: null });
  const [draftModel, setDraftModel] = useState(null); // model chosen before the first message

  const currentIdRef = useRef(null);
  const abortRef = useRef(null);
  const streamingRef = useRef(false);

  const replaceSession = useCallback(
    (session) => setSessions((prev) => prev.map((s) => (s.id === session.id ? session : s))),
    []
  );
  // Sessions are ordered by latest activity, so an updated session moves to the top
  const bumpSession = useCallback(
    (session) => setSessions((prev) => [session, ...prev.filter((s) => s.id !== session.id)]),
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
      .catch(() => {}); // the picker falls back to the server default when Ollama is unreachable
    return () => abortRef.current?.abort();
  }, [refreshSessions]);

  const selectSession = useCallback(async (id) => {
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
    async (assistantId, start) => {
      const controller = new AbortController();
      abortRef.current = controller;
      const patch = (update) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, ...update(m) } : m)));

      try {
        await start({
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "start") patch(() => ({ sources: event.sources }));
            else if (event.type === "token") patch((m) => ({ content: m.content + event.content }));
            else if (event.type === "error") patch(() => ({ error: event.error }));
            else if (event.type === "done") bumpSession(event.session);
          },
        });
      } catch (error) {
        if (error.name === "AbortError") {
          patch(() => ({ stopped: true }));
          refreshSessions(); // the server saved the partial answer and bumped the session
        } else {
          patch(() => ({ error: error.message }));
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
    async (text) => {
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

      await runStream(assistantId, (options) => streamMessage(sessionId, text, options));
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
    async (id) => {
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
    async (id, title) => {
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
    async (model) => {
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
