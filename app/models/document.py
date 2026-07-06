from sqlalchemy import JSON, Enum as SQLAlchemyEnum, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel
from app.schemas.documents import ParseStatus


class Document(BaseModel):
    __tablename__ = "documents"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="문서를 업로드한 사용자(users.id). 이력서 조회 권한 검증에 사용한다.",
    )
    document_type: Mapped[str] = mapped_column(String(50))
    format: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[ParseStatus] = mapped_column(
        SQLAlchemyEnum(
            ParseStatus,
            values_callable=lambda enum: [status.value for status in enum],
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=ParseStatus.PENDING,
        server_default=text("'pending'"),
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
