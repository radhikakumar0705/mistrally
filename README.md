# Mistrally

An AI-powered chat application with secure login, persistent chat memory, and intelligent contextual responses.

---

## Features

- Secure **JWT-based authentication** (Login & Signup)
- **AI chatbot** powered by Mistral model via **Ollama API**
- **Multiple conversations** per user: create, switch between and delete chats (titled from the first message)
- **Chat with your documents (RAG)**: upload PDF or TXT files; relevant passages are retrieved with
  **SentenceTransformer** embeddings and **ChromaDB**, and each user only searches their own documents
- **Persistent chat history** stored in MySQL; the last few turns of a conversation are sent to the model as context
- **Real-time chat interface** with message bubbles, a "thinking" indicator and auto-scroll
- **Error handling**: expired tokens send you back to login; backend errors (e.g. Ollama not running) are shown in the chat
- **Responsive UI** with clean layout using Tailwind CSS

---

## Architecture Overview

### Frontend (React)

- Components: `ChatBubble`, `ChatInput`, `SideBar`, `NavBar`, `ProtectedRoute`
- Pages: `Home`, `Login`, `Signup`, `Chat`, `Notfound`
- API handlers: `axiosClient.js`, `chat.js`, `auth.js`
- Routes managed via React Router
- Token persistence in `localStorage`
- State handled via React Hooks (`useState`, `useEffect`)

### Backend (Flask)

- Modular structure with Blueprints (`auth_bp`, `chat_bp`)
- JWT-based auth using `flask_jwt_extended`
- ORM integration via SQLAlchemy
- AI inference via the **Ollama chat API** (`mistral` by default, set with `OLLAMA_MODEL`)
- Vector retrieval from **ChromaDB** for semantic context
- Message embeddings via **SentenceTransformer (all-MiniLM-L6-v2)**

### Database Layer (MySQL)

- `users` table for credentials
- `chat_sessions` table for conversations
- `chat_history` table for storing user messages and AI responses, per conversation
- SQLAlchemy ORM for query abstraction

### Vector Database

- **ChromaDB** for storing document embeddings
- Persistent vector store (`CHROMA_DB_PATH`, default `./chroma_db`)

---

## Technologies Used

### Frontend

- React.js  
- Tailwind CSS  
- Axios  
- React Router DOM  

### Backend

- Flask  
- Flask-JWT-Extended  
- SQLAlchemy  
- Requests  
- SentenceTransformer  
- ChromaDB  
- Ollama API (Mistral model)  

### Database

- MySQL  

### Misc

- JWT Authentication  
- RESTful API architecture  
- Python virtual environment  

---

## System Flow Diagram 

**Frontend → Flask Backend → Ollama API + MySQL + ChromaDB**

---

## Getting Started

### Prerequisites

- Python 3.10+, Node.js 18+, MySQL 8
- [Ollama](https://ollama.com) running locally, with the model pulled: `ollama pull mistral`

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in SECRET_KEY, JWT_SECRET_KEY and the DB_* values
python app.py                 # http://127.0.0.1:5000, tables are created on first run
```

Create the database first if it doesn't exist: `CREATE DATABASE mistrally;`

**Upgrading an existing database** (created before chat sessions were added): run
`python migrate_add_sessions.py` once from `backend/`. It keeps your old messages by moving
them into an "Earlier chats" conversation.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # REACT_APP_API_URL=http://127.0.0.1:5000
npm start                     # http://localhost:3000
```

---

## API

All `/chat` routes need an `Authorization: Bearer <token>` header from `/auth/login`.

| Method | Route | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an account (`username`, `email`, `password` of 8+ characters) |
| POST | `/auth/login` | Returns `access_token` |
| GET | `/auth/profile` | Current user |
| GET / POST | `/chat/sessions` | List or create conversations |
| DELETE | `/chat/sessions/<id>` | Delete a conversation and its messages |
| GET / POST | `/chat/sessions/<id>/messages` | Read history or send a message (`{"message": "..."}`) |
| POST | `/chat/upload` | Upload a PDF/TXT (`file` form field) to your document store |
