from models.user import User
from repositories.base import SqlAlchemyRepository


class UserRepository(SqlAlchemyRepository[User]):
    model = User

    def by_login(self, identifier: str) -> User | None:
        """Find a user by username, or by email address (case-insensitive)."""
        return User.query.filter((User.username == identifier) | (User.email == identifier.lower())).first()

    def by_username(self, username: str) -> User | None:
        return User.query.filter_by(username=username).first()

    def by_email(self, email: str) -> User | None:
        return User.query.filter_by(email=email.lower()).first()

    def by_google_sub(self, sub: str) -> User | None:
        return User.query.filter_by(google_sub=sub).first()

    def exists(self, username: str, email: str) -> bool:
        return User.query.filter((User.username == username) | (User.email == email)).first() is not None

    def all(self) -> list[User]:
        return User.query.all()
