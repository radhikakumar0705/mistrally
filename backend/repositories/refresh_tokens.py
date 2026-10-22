from datetime import datetime

from models.refresh_token import RefreshToken
from repositories.base import SqlAlchemyRepository


class RefreshTokenRepository(SqlAlchemyRepository[RefreshToken]):
    model = RefreshToken

    def by_jti(self, jti: str) -> RefreshToken | None:
        return RefreshToken.query.filter_by(jti=jti).first()

    def revoke_all_for_user(self, user_id: int, when: datetime) -> None:
        RefreshToken.query.filter_by(user_id=user_id, revoked_at=None).update({"revoked_at": when})
