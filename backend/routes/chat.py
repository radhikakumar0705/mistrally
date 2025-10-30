from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.chat_history import ChatHistory
import requests
import chromadb
from sentence_transformers import SentenceTransformer
import os

chat_bp = Blueprint('chat', __name__)

CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
OLLAMA_URL = "http://localhost:11434/api/generate"
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection("chat_docs")

@chat_bp.route("/send", methods=["POST"])
@jwt_required()
def chat():
    user_id = get_jwt_identity()
    data = request.get_json()
    user_msg = data.get("message")

    if not user_msg:
        return jsonify({"error": "Message is required"}), 400

    query_emb = EMBED_MODEL.encode(user_msg).tolist()
    results = collection.query(query_embeddings=[query_emb], n_results=3)

    retrieved_context = " ".join(results["documents"][0]) if results["documents"] else ""

    history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(5).all()
    conversation_context = "\n".join([f"User: {h.user_message}\nBot: {h.bot_response}" for h in reversed(history)])

   
    prompt = f"""
    You are Mistrally, a helpful AI teaching assistant.
    Context from memory: {retrieved_context}
    Conversation so far:
    {conversation_context}
    New message: {user_msg}
    """

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    try:
        res = requests.post(OLLAMA_URL, json=payload)
        if res.status_code != 200:
            return jsonify({"error": "Ollama request failed", "details": res.text}), 500

        bot_response = res.json().get("response", "").strip()


        chat_entry = ChatHistory(
            user_id=user_id,
            user_message=user_msg,
            bot_response=bot_response
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({"response": bot_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route("/history", methods=["GET"])
@jwt_required()
def get_chat_history():
    print("Authorization Header:", request.headers.get("Authorization"))
    user_id = get_jwt_identity()

    history = (
        ChatHistory.query.filter_by(user_id=user_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(10)
        .all()
    )
   

    data = [h.to_dict() for h in reversed(history)]  
    return jsonify(data), 200
