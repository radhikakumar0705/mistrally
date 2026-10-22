"""Accounts: registration, password login and Google sign-in rules, independent of HTTP."""
import re
import secrets

from models.user import User
from repositories import UserRepository
from services.errors import Conflict, InvalidInput, NotFound, Unauthorized

MIN_PASSWORD_LENGTH = 8


class GoogleSignInError(Exception):
    """Google sign-in can't complete; `code` becomes the ?error= shown on the login page."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class AuthService:
    def __init__(self, users=None):
        self.users = users or UserRepository()

    def register(self, username, email, password) -> User:
        username = (username or "").strip()
        email = (email or "").strip().lower()
        password = password or ""
        if not username or not email or not password:
            raise InvalidInput("Missing required fields")
        if len(username) > 50:
            raise InvalidInput("Username must be 50 characters or fewer")
        if "@" not in email:
            raise InvalidInput("Invalid email address")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidInput(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if self.users.exists(username, email):
            raise Conflict("User already exists")

        user = User(username=username, email=email)
        user.set_password(password)
        self.users.add(user)
        self.users.commit()
        return user

    def authenticate(self, identifier, password) -> User:
        identifier = (identifier or "").strip()
        password = password or ""
        if not identifier or not password:
            raise InvalidInput("Missing username or password")
        user = self.users.by_login(identifier)
        if user and not user.password and user.google_sub:
            raise InvalidInput('This account signs in with Google. Use "Continue with Google".')
        if not user or not user.check_password(password):
            raise Unauthorized("Invalid credentials")
        return user

    def profile(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFound("User not found")
        return user

    # ---- Google ----

    @staticmethod
    def _verified_identity(info: dict) -> tuple[str, str]:
        sub, email = info.get("sub"), (info.get("email") or "").lower()
        if not sub or not email or not info.get("email_verified"):
            raise GoogleSignInError("google_unverified")
        return sub, email

    def _unique_username(self, email: str) -> str:
        base = re.sub(r"[^a-z0-9_.]", "", email.split("@")[0].lower())[:40] or "user"
        username = base
        while self.users.by_username(username):
            username = f"{base}{secrets.randbelow(10000):04d}"
        return username

    def google_sign_in(self, info: dict) -> User:
        """Sign in with a Google identity, creating the account on first use."""
        sub, email = self._verified_identity(info)
        user = self.users.by_google_sub(sub)
        if user is not None:
            return user
        if self.users.by_email(email):
            # Emails are not verified at sign-up, so a password account with this address may not belong
            # to this Google user. Linking must be done from inside that account instead.
            raise GoogleSignInError("account_exists")
        user = User(
            username=self._unique_username(email),
            email=email,
            google_sub=sub,
            name=info.get("name"),
            avatar_url=info.get("picture"),
        )
        self.users.add(user)
        self.users.commit()
        return user

    def link_google(self, user_id: int, info: dict) -> User:
        """Connect a Google identity to an existing (signed-in) account."""
        sub, _email = self._verified_identity(info)
        user = self.users.get(user_id)
        if user is None:
            raise GoogleSignInError("session_expired")
        existing = self.users.by_google_sub(sub)
        if existing and existing.id != user.id:
            raise GoogleSignInError("already_linked")
        user.google_sub = sub
        user.avatar_url = user.avatar_url or info.get("picture")
        user.name = user.name or info.get("name")
        self.users.commit()
        return user
