"""
Domain errors raised by the service layer.

Services never build HTTP responses. They raise one of these, and a single error handler in app.py
turns it into a JSON response with the matching status code. The message is always safe to show users.
"""


class DomainError(Exception):
    status = 400

    def __init__(self, message: str, *, status: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status
        self.payload = payload or {}  # extra fields to include in the response body

    def to_dict(self) -> dict:
        return {**self.payload, "error": self.message}


class InvalidInput(DomainError):
    status = 400


class Unauthorized(DomainError):
    status = 401


class NotFound(DomainError):
    status = 404


class Conflict(DomainError):
    status = 409


class Unprocessable(DomainError):
    status = 422


class DependencyUnavailable(DomainError):
    """A downstream system (model, vector store, queue, sandbox) is unavailable."""

    status = 502
