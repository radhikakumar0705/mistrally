"""Study mode use cases: generate quizzes/flashcards and run code, independent of HTTP."""
import requests
from flask import current_app

from services import study
from services.document_service import DocumentService
from services.errors import DependencyUnavailable, InvalidInput, NotFound

MAX_COUNT = {"quiz": 10, "flashcards": 20}
DIFFICULTIES = ("easy", "medium", "hard")


class StudyService:
    def __init__(self, documents: DocumentService | None = None, generator=study):
        self.documents = documents or DocumentService()
        self.generator = generator

    def create(self, user_id: int, kind: str, request: dict) -> dict:
        try:
            count = int(request.get("count", 5))
        except (TypeError, ValueError) as e:
            raise InvalidInput("count must be a number") from e
        if not 1 <= count <= MAX_COUNT[kind]:
            raise InvalidInput(f"count must be between 1 and {MAX_COUNT[kind]}")
        difficulty = request.get("difficulty", "medium")
        if difficulty not in DIFFICULTIES:
            raise InvalidInput("difficulty must be easy, medium or hard")

        topic = (request.get("topic") or "").strip()[:200]
        context = None
        if request.get("document_id"):
            document, context = self.documents.study_text(user_id, request["document_id"])
            topic = topic or document.filename
        elif not topic:
            raise InvalidInput("Choose a document or enter a topic")

        try:
            result = self.generator.generate(
                kind, count=count, difficulty=difficulty, topic=topic, context=context,
                model=request.get("model") or None,
            )
        except study.StudyError as e:
            raise DependencyUnavailable(str(e)) from e
        return {"kind": kind, "source": topic, **result}


class SandboxClient:
    """Calls the isolated code-runner service (see sandbox/)."""

    MAX_CODE_CHARS = 20_000
    MAX_STDIN_CHARS = 10_000

    def __init__(self, base_url: str | None = None, token: str | None = None):
        config = current_app.config
        self.base_url = (base_url if base_url is not None else config.get("SANDBOX_URL")) or None
        self.token = token if token is not None else config.get("SANDBOX_TOKEN", "")

    def run(self, code, stdin="", language="python") -> dict:
        if not self.base_url:
            raise NotFound("The code runner is not enabled")
        code = code or ""
        if not code.strip():
            raise InvalidInput("No code to run")
        if len(code) > self.MAX_CODE_CHARS:
            raise InvalidInput("That code is too long to run")
        if (language or "python") != "python":
            raise InvalidInput("Only Python can be run")
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/run",
                json={"code": code, "stdin": (stdin or "")[: self.MAX_STDIN_CHARS]},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=20,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            current_app.logger.exception("Sandbox request failed")
            raise DependencyUnavailable("The code runner is unavailable") from e
        return response.json()
