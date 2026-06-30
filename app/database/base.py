import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLAlchemyEnum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def enum_column(enum_cls: type[enum.Enum], name: str, *, length: int = 20) -> SQLAlchemyEnum:
    """Enum 값(.value 문자열)으로 저장하는 비네이티브 enum 컬럼 타입(VARCHAR + CHECK)을 만든다.

    Args:
        enum_cls: 저장할 Enum 클래스.
        name: 생성될 CHECK 제약 이름의 기반(SQLAlchemy Enum name).
        length: 저장 컬럼의 VARCHAR 길이.

    Returns:
        mapped_column에 넘길 SQLAlchemy Enum 타입.
    """
    return SQLAlchemyEnum(
        enum_cls,
        values_callable=lambda enum_type: [member.value for member in enum_type],
        native_enum=False,
        create_constraint=True,
        length=length,
        name=name,
    )


class BaseModel(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
