# Mistrally

**Description:**  
An AI-powered chat application with secure login, persistent chat memory, and intelligent contextual responses.

---

## Features

- Secure **JWT-based authentication** (Login & Signup)
- **AI chatbot** powered by Mistral model via **Ollama API**
- **Context-aware responses** using **SentenceTransformer** embeddings and **ChromaDB** vector search
- **Persistent chat history** stored in MySQL (per-user conversation tracking)
- **Real-time chat interface** with message bubbles and auto-scroll
- **User session management** using `localStorage`
- **Error handling** for invalid tokens and failed API requests
- **Responsive UI** with clean layout using Tailwind CSS

---

## Architecture Overview

### Frontend (React)

- Components: `ChatBubble`, `ChatInput`, `Login`, `Signup`
- API handlers: `axiosClient.js`, `chatApi.js`, `authApi.js`
- Routes managed via React Router
- Token persistence in `localStorage`
- State handled via React Hooks (`useState`, `useEffect`)

### Backend (Flask)

- Modular structure with Blueprints (`auth_bp`, `chat_bp`)
- JWT-based auth using `flask_jwt_extended`
- ORM integration via SQLAlchemy
- AI inference via **Ollama API** (`mistral` model)
- Vector retrieval from **ChromaDB** for semantic context
- Message embeddings via **SentenceTransformer (all-MiniLM-L6-v2)**

### Database Layer (MySQL)

- `users` table for credentials
- `chat_history` table for storing user messages and AI responses
- SQLAlchemy ORM for query abstraction

### Vector Database

- **ChromaDB** for storing document embeddings
- Persistent vector store (`./chroma_db`)

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
