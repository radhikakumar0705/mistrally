// src/pages/ChatPage.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import chat from "../api/chat";

const Chat = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);

  // Send message
  const handleSend = async (msg) => {
    const userMsg = { sender: "user", text: msg };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await chat.sendMessage(msg);
      const botMsg = { sender: "bot", text: res.response || res.bot_response || "No reply"};
      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errMsg = { sender: "bot", text: "⚠️ Failed to send message." };
      setMessages((prev) => [...prev, errMsg]);
    }
  };

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem("token");

      // Redirect to login if not authenticated
      if (!token) {
        console.warn("No token found. Redirecting to login...");
        navigate("/login");
        return;
      }

      try {
        const history = await chat.getHistory();
        if (Array.isArray(history)) {
          const formatted = history.flatMap((h) => [
            { sender: "user", text: h.user_message },
            { sender: "bot", text: h.bot_response },
          ]);
          setMessages(formatted);
        }

      } catch (error) {
        console.error("Error fetching chat history:", error);
      }
    })();
  }, [navigate]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((msg, idx) => (
          <ChatBubble key={idx} sender={msg.sender} text={msg.text} />
        ))}
      </div>
      <ChatInput onSend={handleSend} />
    </div>
  );
};

export default Chat;
