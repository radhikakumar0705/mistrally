// src/pages/Chat.jsx
import { useState, useEffect, useRef } from "react";
import Sidebar from "../components/SideBar";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import { errorMessage } from "../api/axiosClient";
import {
  getSessionMessages,
  sendMessage,
  createSession,
  deleteSession,
  getChatSessions,
  uploadDocument,
} from "../api/chat";

const toBubbles = (history) =>
  history.flatMap((h) => [
    { sender: "user", text: h.user_message },
    { sender: "bot", text: h.bot_response },
  ]);

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]); // All chat sessions
  const [currentSessionId, setCurrentSessionId] = useState(null); // Active session
  const [waiting, setWaiting] = useState(false);
  const bottomRef = useRef(null);

  const addBubble = (sender, text) =>
    setMessages((prev) => [...prev, { sender, text }]);

  // Load messages of the selected session
  const selectSession = async (sessionId) => {
    setCurrentSessionId(sessionId);
    setMessages([]);
    try {
      setMessages(toBubbles(await getSessionMessages(sessionId)));
    } catch (err) {
      console.error("Error loading session messages:", err);
    }
  };

  // Create a new chat session and make it active
  const startNewChat = async () => {
    const session = await createSession();
    setSessions((prev) => [session, ...prev]);
    setCurrentSessionId(session.id);
    return session.id;
  };

  const handleNewChat = async () => {
    try {
      await startNewChat();
      setMessages([]);
    } catch (err) {
      console.error("Error creating session:", err);
    }
  };

  const handleDelete = async (sessionId) => {
    if (!window.confirm("Delete this chat?")) return;
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (sessionId === currentSessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Error deleting session:", err);
    }
  };

  // Send message to current session, starting one if needed
  const handleSend = async (msg) => {
    addBubble("user", msg);
    setWaiting(true);

    try {
      const sessionId = currentSessionId ?? (await startNewChat());
      const res = await sendMessage(sessionId, msg);
      addBubble("bot", res.response || "No reply");
      // The first message titles the session
      setSessions((prev) => prev.map((s) => (s.id === res.session.id ? res.session : s)));
    } catch (error) {
      console.error("Error sending message:", error);
      addBubble("bot", `⚠️ ${errorMessage(error, "Failed to send message.")}`);
    } finally {
      setWaiting(false);
    }
  };

  const handleUpload = async (file) => {
    setWaiting(true);
    try {
      const res = await uploadDocument(file);
      addBubble("bot", `📄 Added "${res.filename}" to your documents. Ask me about it!`);
    } catch (error) {
      addBubble("bot", `⚠️ ${errorMessage(error, "Upload failed.")}`);
    } finally {
      setWaiting(false);
    }
  };

  // Initial load: list sessions and open the most recent one
  useEffect(() => {
    (async () => {
      try {
        const data = await getChatSessions();
        setSessions(data);
        if (data.length > 0) selectSession(data[0].id);
      } catch (err) {
        console.error("Failed to load sessions:", err);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the newest message in view
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting]);

  return (
    <div className="flex h-[calc(100vh-8rem)] rounded-lg overflow-hidden shadow">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={selectSession}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
      />
      <div className="flex flex-col flex-1 bg-gray-50">
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 && !waiting && (
            <p className="text-center text-gray-400 mt-10">
              Ask Mistrally anything, or attach a PDF/TXT with 📎 to chat about it.
            </p>
          )}
          {messages.map((msg, idx) => (
            <ChatBubble key={idx} sender={msg.sender} text={msg.text} />
          ))}
          {waiting && <ChatBubble sender="bot" text="Mistrally is thinking…" />}
          <div ref={bottomRef} />
        </div>
        <ChatInput onSend={handleSend} onUpload={handleUpload} disabled={waiting} />
      </div>
    </div>
  );
};

export default ChatPage;
