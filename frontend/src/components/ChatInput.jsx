import { useRef, useState } from "react";

const ChatInput = ({ onSend, onUpload, disabled }) => {
  const [message, setMessage] = useState("");
  const fileInput = useRef(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = "";
  };

  return (
    <div className="flex items-center p-3 bg-gray-50">
      <input
        type="file"
        accept=".pdf,.txt"
        ref={fileInput}
        onChange={handleFile}
        className="hidden"
      />
      <button
        onClick={() => fileInput.current?.click()}
        disabled={disabled}
        title="Add a PDF or TXT document for Mistrally to use"
        className="border border-gray-300 text-gray-600 px-3 py-2 rounded-lg mr-2 hover:bg-gray-200 disabled:opacity-50"
      >
        📎
      </button>
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
        disabled={disabled}
        className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
      >
        Send
      </button>
    </div>
  );
};

export default ChatInput;
