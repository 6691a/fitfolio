from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import mapped_column, Mapped

from app.database.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "char_length(nickname) >= 2",
            name="ck_users_nickname_min_length",
        ),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column("password", String(255))
    nickname: Mapped[str] = mapped_column(String(50), unique=True, index=True)
