import json

import requests
from flask import current_app

SYSTEM_PROMPT = (
    "You are Mistrally, a helpful AI teaching assistant for programmers. "
    "Give simple, clear explanations, and include code examples whenever the question calls for them. "
    "Format answers in Markdown and put code in fenced code blocks with a language tag."
)


class OllamaError(Exception):
    """Raised when the local Ollama server cannot produce a response."""


def build_messages(history, context_chunks, user_message):
    """
    Build an Ollama /api/chat message list: system prompt (plus any retrieved
    document excerpts), the previous turns of this conversation, then the new message.
    """
    system = SYSTEM_PROMPT
    if context_chunks:
        excerpts = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in context_chunks)
        system += (
            "\n\nThe user has uploaded documents. These excerpts may help; use them when they are "
            "relevant and mention the document name you used:\n\n" + excerpts
        )

    messages = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": "user", "content": turn.user_message})
        messages.append({"role": "assistant", "content": turn.bot_response})
    messages.append({"role": "user", "content": user_message})
    return messages


def _describe(error):
    """Prefer Ollama's own error message (e.g. "model 'x' not found") over the HTTP status."""
    response = getattr(error, "response", None)
    if response is not None:
        try:
            return response.json().get("error") or str(error)
        except ValueError:
            pass
    if isinstance(error, requests.exceptions.ConnectionError):
        return "Could not connect to Ollama. Is it running?"
    return str(error)


def stream_chat(messages, model):
    """
    Start a streaming chat completion and return a generator of text pieces.
    Connection problems raise OllamaError here, before anything is streamed,
    so the route can still answer with a normal error status.
    """
    config = current_app.config
    try:
        response = requests.post(
            f"{config['OLLAMA_URL']}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            stream=True,
            timeout=(5, config["OLLAMA_TIMEOUT"]),
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise OllamaError(_describe(e)) from e

    def pieces():
        # Closing this generator closes the HTTP response, which tells Ollama to stop generating.
        with response:
            try:
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise OllamaError(data["error"])
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
                    if data.get("done"):
                        return
            except requests.exceptions.RequestException as e:
                raise OllamaError(_describe(e)) from e

    return pieces()


def list_models():
    """Names of the models installed in the local Ollama."""
    config = current_app.config
    try:
        response = requests.get(f"{config['OLLAMA_URL']}/api/tags", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise OllamaError(_describe(e)) from e
    return sorted(m["name"] for m in response.json().get("models", []))
