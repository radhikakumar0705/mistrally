import requests
from flask import current_app

SYSTEM_PROMPT = (
    "You are Mistrally, a helpful AI teaching assistant for programmers. "
    "Give simple, clear explanations, and include code examples whenever the question calls for them."
)


class OllamaError(Exception):
    """Raised when the local Ollama server cannot produce a response."""


def build_messages(history, context, user_message):
    """
    Build an Ollama /api/chat message list: system prompt (plus any retrieved
    document context), the previous turns of this conversation, then the new message.
    """
    system = SYSTEM_PROMPT
    if context:
        system += (
            "\n\nUse these excerpts from the user's uploaded documents when they are relevant:\n"
            + context
        )

    messages = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": "user", "content": turn.user_message})
        messages.append({"role": "assistant", "content": turn.bot_response})
    messages.append({"role": "user", "content": user_message})
    return messages


def chat(messages):
    """Send a conversation to the local model via Ollama and return its reply."""
    config = current_app.config
    try:
        response = requests.post(
            f"{config['OLLAMA_URL']}/api/chat",
            json={"model": config["OLLAMA_MODEL"], "messages": messages, "stream": False},
            timeout=config["OLLAMA_TIMEOUT"],
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise OllamaError(str(e)) from e

    return response.json().get("message", {}).get("content", "").strip()
