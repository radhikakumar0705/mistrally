const ChatBubble = ({ sender, text }) => {
  const isUser = sender === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}
    >
      <div
        className={`px-4 py-3 rounded-2xl shadow-sm max-w-[80%] break-words ${
          isUser
            ? "bg-blue-500 text-white rounded-br-none"
            : "bg-gray-200 text-gray-800 rounded-bl-none"
        }`}
        style={{
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
        }}
      >
        {text}
      </div>
    </div>
  );
};

export default ChatBubble;
