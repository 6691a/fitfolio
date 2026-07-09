from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class UserPreferences(BaseModel):
    """관심 직무·기술의 사용자 override. 최근 분석에서 자동 추출한 제안값을 사용자가 수정·저장하면 여기 남는다.

    사용자당 1행이며 LLM 답변 개인화에 쓴다. 비어 있는 필드는 자동 추출 제안값으로 대체된다.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="개인화 프로필 소유자(users.id). 사용자당 1행만 가진다.",
    )
    interest_jobs: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="관심 직무(사용자 수정본). 비면 자동 추출값을 쓴다. 예: '백엔드 개발자, 데이터 엔지니어'.",
    )
    interest_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="관심 기술/역량(사용자 수정본). 비면 자동 추출값을 쓴다. 예: 'Python, AWS, Kafka'.",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="강조하고 싶은 점·답변 톤 등 자유 기타 메모.",
    )
