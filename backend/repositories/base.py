from typing import Generic, TypeVar

from extensions import db

Model = TypeVar("Model", bound=db.Model)


class SqlAlchemyRepository(Generic[Model]):
    """Common operations on one model class, using the request's SQLAlchemy session."""

    model: type[Model]

    def __init__(self, session=None):
        self.session = session or db.session

    def get(self, entity_id) -> Model | None:
        return self.session.get(self.model, entity_id)

    def add(self, entity: Model) -> Model:
        self.session.add(entity)
        return entity

    def delete(self, entity: Model) -> None:
        self.session.delete(entity)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
