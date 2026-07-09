from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel, enum_column
from app.schemas.documents import ParseStatus


class FitAnalysis(BaseModel):
    """이력서 × 채용공고 적합도 분석 요청과 결과를 저장하는 테이블."""

    __tablename__ = "fit_analyses"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        comment="분석을 요청한 사용자(users.id). 결과 조회 권한 검증에 사용한다.",
    )
    resume_document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        comment="분석 대상 이력서 문서(documents.id).",
    )
    job_posting_document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        comment="분석 대상 채용공고 문서(documents.id).",
    )
    status: Mapped[ParseStatus] = mapped_column(
        enum_column(ParseStatus, "fit_analysis_status"),
        default=ParseStatus.PENDING,
        server_default=text("'pending'"),
        comment="분석 진행 상태(pending/started/retry/done/failed).",
    )
    result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="FitAnalysisResult 직렬화 JSON. 완료 전에는 NULL.",
    )
    interview_preparation: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="InterviewPreparationResult 직렬화 JSON. 사용자가 요청한 뒤 생성·캐시한다.",
    )
    feedback: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="사용자 피드백 {rating: up|down, note: str}. 다음 분석 개인화에 쓴다. 없으면 NULL.",
    )
    error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="분석 실패 시 오류 메시지.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="soft delete 시각. NULL이면 조회 대상, 값이 있으면 삭제된 것으로 간주해 숨긴다.",
    )
