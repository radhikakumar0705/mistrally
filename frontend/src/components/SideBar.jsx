const Sidebar = ({ sessions, currentSessionId, onSelect, onNewChat, onDelete }) => {
  return (
    <div className="w-64 bg-gray-900 text-white p-4 flex flex-col">
      <button
        onClick={onNewChat}
        className="bg-green-600 p-2 rounded mb-4 hover:bg-green-700"
      >
        + New Chat
      </button>

      <div className="flex-1 overflow-y-auto">
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`group flex items-center justify-between p-2 mb-2 rounded cursor-pointer ${
              s.id === currentSessionId ? "bg-gray-700" : "bg-gray-800 hover:bg-gray-700"
            }`}
          >
            <span className="truncate">{s.title || "Untitled Chat"}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
              title="Delete chat"
              className="ml-2 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
