import json

import requests

from services.llm.base import LLMError, Provider, describe_http_error, parse_json


class OllamaProvider(Provider):
    """Local models served by Ollama (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

    name = "ollama"

    def __init__(self, base_url, timeout):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path, payload, stream=False):
        try:
            response = requests.post(
                f"{self.base_url}{path}", json=payload, stream=stream, timeout=(5, self.timeout)
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(describe_http_error(e, "Ollama")) from e
        return response

    def stream_chat(self, messages, model):
        response = self._post("/api/chat", {"model": model, "messages": messages, "stream": True}, stream=True)

        def pieces():
            # Closing this generator closes the HTTP response, which tells Ollama to stop generating.
            with response:
                try:
                    for line in response.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise LLMError(data["error"])
                        content = data.get("message", {}).get("content")
                        if content:
                            yield content
                        if data.get("done"):
                            return
                except requests.exceptions.RequestException as e:
                    raise LLMError(describe_http_error(e, "Ollama")) from e

        return pieces()

    def complete_json(self, messages, model, schema):
        # Ollama constrains generation to the JSON schema itself ("structured outputs")
        response = self._post(
            "/api/chat",
            {"model": model, "messages": messages, "stream": False, "format": schema, "options": {"temperature": 0.3}},
        )
        return parse_json(response.json().get("message", {}).get("content", ""))

    def list_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(describe_http_error(e, "Ollama")) from e
        return sorted(m["name"] for m in response.json().get("models", []))
