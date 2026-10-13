import time

from services.llm.base import Provider

CANNED_ANSWER = (
    "Here's a quick example in Python:\n\n"
    "```python\n"
    "def greet(name):\n"
    "    return f\"Hello, {name}!\"\n"
    "```\n\n"
    "This is the **demo model**, so the answer is canned. Your question was: "
)


class FakeProvider(Provider):
    """
    A deterministic stand-in model for end-to-end tests, load tests and demos without an LLM.
    It streams a fixed Markdown answer word by word and returns schema-shaped JSON.
    """

    name = "fake"

    def __init__(self, delay=0.02):
        self.delay = delay

    def stream_chat(self, messages, model):
        question = messages[-1]["content"] if messages else ""
        text = CANNED_ANSWER + f"\"{question}\""

        def pieces():
            for i, word in enumerate(text.split(" ")):
                if self.delay:
                    time.sleep(self.delay)
                yield word if i == 0 else " " + word

        return pieces()

    def complete_json(self, messages, model, schema):
        return _example_for(schema)

    def list_models(self):
        return ["fake-tutor"]


def _example_for(schema):
    """Build a small valid instance of a JSON schema (enough for quizzes and flashcards)."""
    kind = schema.get("type")
    if kind == "object":
        return {key: _example_for(sub) for key, sub in schema.get("properties", {}).items()}
    if kind == "array":
        count = max(schema.get("minItems", 3), 1)
        return [_example_for(schema.get("items", {})) for _ in range(count)]
    if kind == "integer":
        return schema.get("minimum", 0)
    if kind == "boolean":
        return True
    if "enum" in schema:
        return schema["enum"][0]
    return "Example text"
