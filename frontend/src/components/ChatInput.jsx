import { useState } from "react";

const ChatInput = ({ onSend }) => {
  const [message, setMessage] = useState("");

  const handleSend = () => {
    if (message.trim()) {
      onSend(message);
      setMessage("");
    }
  };

  return (
    <div className="flex items-center p-3 bg-gray-50">
      <input
        type="text"
        placeholder="Type a message..."
        className="flex-1 border rounded-lg px-3 py-2 mr-2 focus:outline-none focus:ring focus:ring-blue-400 text-black"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
      />
      <button
        onClick={handleSend}
        className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
      >
        Send
      </button>
    </div>
  );
};

export default ChatInput;
