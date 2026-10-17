"""
Quiz and flashcard generation with schema-checked model output.

The Pydantic models below are the contract: their JSON schema is sent to the model (Ollama enforces it
during generation; OpenAI-compatible APIs get it in the prompt with JSON mode), and the reply is validated
against the same models. Invalid output is retried once, then reported as an error instead of shown.
"""
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError, field_validator

from services import llm

MAX_CONTEXT_CHARS = 6000


class QuizQuestion(BaseModel):
    question: Annotated[str, Field(min_length=5, max_length=500)]
    options: Annotated[list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=4, max_length=4)]
    answer_index: Annotated[int, Field(ge=0, le=3)]
    explanation: Annotated[str, Field(min_length=1, max_length=600)]

    @field_validator("options")
    @classmethod
    def options_are_distinct(cls, options):
        if len({o.strip().lower() for o in options}) != len(options):
            raise ValueError("options must be distinct")
        return options


class Quiz(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    questions: Annotated[list[QuizQuestion], Field(min_length=1, max_length=10)]


class Flashcard(BaseModel):
    front: Annotated[str, Field(min_length=1, max_length=300)]
    back: Annotated[str, Field(min_length=1, max_length=600)]


class FlashcardDeck(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    cards: Annotated[list[Flashcard], Field(min_length=1, max_length=20)]


KINDS = {"quiz": Quiz, "flashcards": FlashcardDeck}


class StudyError(Exception):
    """Generation failed; the message is safe to show."""


def inline_schema(schema):
    """Resolve $ref/$defs into one self-contained schema (simplest for every provider's JSON mode)."""
    definitions = schema.get("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(definitions[node["$ref"].split("/")[-1]])
            return {k: resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def _prompt(kind, count, difficulty, topic, context):
    if kind == "quiz":
        task = (
            f"Write a {difficulty} multiple-choice quiz with exactly {count} questions. Each question has "
            "exactly 4 distinct options, the index (0-3) of the single correct option, and a one-sentence "
            "explanation of why it is correct."
        )
    else:
        task = (
            f"Write exactly {count} flashcards. The front is a short question or term; the back is a concise "
            "answer of one or two sentences."
        )
    source = (
        f"Base everything strictly on this study material:\n\n{context}"
        if context
        else f"The topic is: {topic}"
    )
    return [
        {"role": "system", "content": "You are Mistrally, a programming tutor who writes accurate study material."},
        {"role": "user", "content": f"{task}\nGive it a short title. {source}"},
    ]


def generate(kind, *, count, difficulty="medium", topic=None, context=None, model=None):
    schema_model = KINDS[kind]
    messages = _prompt(kind, count, difficulty, topic, context[:MAX_CONTEXT_CHARS] if context else None)
    schema = inline_schema(schema_model.model_json_schema())
    model = model or llm.default_model()

    last_error = None
    for _attempt in range(2):
        try:
            raw = llm.complete_json(messages, model, schema)
            result = schema_model.model_validate(raw)
        except (ValidationError, llm.LLMError) as e:
            last_error = e
            continue
        items = result.questions if kind == "quiz" else result.cards
        del items[count:]  # models sometimes overshoot the requested number
        return result.model_dump()

    if isinstance(last_error, llm.LLMError) and "JSON" not in str(last_error):
        raise StudyError(f"The AI model is unavailable: {last_error}")
    raise StudyError("The model returned an invalid quiz. Please try again.")

