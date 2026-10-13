import json

import requests

from services.llm.base import LLMError, Provider, describe_http_error, parse_json


class OpenAICompatibleProvider(Provider):
    """
    Any OpenAI-compatible chat completions API: Groq (the hosted demo), OpenAI, Together, vLLM, LM Studio...
    """

    def __init__(self, name, base_url, api_key, timeout, models=None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.models = models  # optional allow-list shown in the model picker

    def _headers(self):
        if not self.api_key:
            raise LLMError(f"No API key configured for {self.name}")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _post(self, payload, stream=False):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                stream=stream,
                timeout=(5, self.timeout),
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(describe_http_error(e, self.name)) from e
        return response

    def stream_chat(self, messages, model):
        response = self._post({"model": model, "messages": messages, "stream": True}, stream=True)

        def pieces():
            with response:
                try:
                    for raw in response.iter_lines():
                        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        event = json.loads(data)
                        if event.get("error"):
                            raise LLMError(str(event["error"]))
                        choices = event.get("choices") or [{}]
                        content = (choices[0].get("delta") or {}).get("content")
                        if content:
                            yield content
                except requests.exceptions.RequestException as e:
                    raise LLMError(describe_http_error(e, self.name)) from e

        return pieces()

    def complete_json(self, messages, model, schema):
        # JSON mode is widely supported; the schema itself goes in the prompt and is validated afterwards
        instruction = {
            "role": "system",
            "content": "Respond only with a JSON object matching this JSON schema:\n" + json.dumps(schema),
        }
        response = self._post({
            "model": model,
            "messages": [instruction, *messages],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        })
        choices = response.json().get("choices") or [{}]
        return parse_json(choices[0].get("message", {}).get("content", ""))

    def list_models(self):
        if self.models:
            return sorted(self.models)
        try:
            response = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(describe_http_error(e, self.name)) from e
        return sorted(m["id"] for m in response.json().get("data", []))
