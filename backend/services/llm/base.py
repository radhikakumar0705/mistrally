import json
from abc import ABC, abstractmethod

import requests


class LLMError(Exception):
    """The language model could not produce a response."""


class Provider(ABC):
    """A chat model backend. Every provider streams plain text pieces and can return JSON."""

    name = "base"

    @abstractmethod
    def stream_chat(self, messages, model):
        """
        Start a streaming completion and return a generator of text pieces. Problems that stop the
        request from starting raise LLMError here, so routes can still answer with an error status.
        """

    @abstractmethod
    def complete_json(self, messages, model, schema):
        """A single non-streaming completion constrained to JSON; returns the parsed object."""

    @abstractmethod
    def list_models(self):
        """Names of the models this provider can use."""


def describe_http_error(error, service):
    """Prefer the provider's own error message (e.g. "model 'x' not found") over the HTTP status."""
    response = getattr(error, "response", None)
    if response is not None:
        try:
            body = response.json()
            message = body.get("error")
            if isinstance(message, dict):
                message = message.get("message")
            if message:
                return message
        except ValueError:
            pass
    if isinstance(error, requests.exceptions.ConnectionError):
        return f"Could not connect to {service}. Is it running?"
    return str(error)


def parse_json(text):
    """Parse model output as JSON, tolerating a Markdown code fence around it."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except ValueError as e:
        raise LLMError("The model did not return valid JSON") from e
