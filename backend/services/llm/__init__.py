"""
Model provider layer (Strategy pattern). `Provider` is the strategy interface (stream_chat,
complete_json, list_models); each backend is a concrete strategy, and `get_provider()` picks one from
configuration, so callers like ChatService never depend on a specific model API. LLM_PROVIDER selects:

    ollama  local models via Ollama (default)
    groq    Groq's OpenAI-compatible API (used for the hosted demo)
    openai  OpenAI or any other OpenAI-compatible endpoint (OPENAI_BASE_URL)
    fake    a deterministic canned model for tests, load tests and demos without an LLM
"""
from flask import current_app

from services.llm.base import LLMError, Provider
from services.llm.fake import FakeProvider
from services.llm.ollama import OllamaProvider
from services.llm.openai_compat import OpenAICompatibleProvider

__all__ = ["LLMError", "Provider", "complete_json", "default_model", "get_provider", "list_models", "stream_chat"]

DEFAULT_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "fake": "fake-tutor",
}


def get_provider():
    config = current_app.config
    name = config["LLM_PROVIDER"]
    if name == "ollama":
        return OllamaProvider(config["OLLAMA_URL"], config["OLLAMA_TIMEOUT"])
    if name == "groq":
        return OpenAICompatibleProvider(
            "Groq", "https://api.groq.com/openai/v1", config["GROQ_API_KEY"], config["OLLAMA_TIMEOUT"],
            models=config["LLM_MODELS"],
        )
    if name == "openai":
        return OpenAICompatibleProvider(
            "OpenAI", config["OPENAI_BASE_URL"], config["OPENAI_API_KEY"], config["OLLAMA_TIMEOUT"],
            models=config["LLM_MODELS"],
        )
    if name == "fake":
        return FakeProvider(delay=config["FAKE_LLM_DELAY"])
    raise LLMError(f"Unknown LLM_PROVIDER '{name}'")


def default_model():
    config = current_app.config
    if config.get("LLM_MODEL"):
        return config["LLM_MODEL"]
    if config["LLM_PROVIDER"] == "ollama":
        return config["OLLAMA_MODEL"]
    return DEFAULT_MODELS.get(config["LLM_PROVIDER"], config["OLLAMA_MODEL"])


def stream_chat(messages, model):
    return get_provider().stream_chat(messages, model)


def complete_json(messages, model, schema):
    return get_provider().complete_json(messages, model, schema)


def list_models():
    return get_provider().list_models()
