from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.documents import ParseStatus


class FitDimension(BaseModel):
    score: int = Field(ge=0, le=100, description="이 항목의 적합도 점수(0~100 정수)")
    comment: str = Field(description="점수 근거를 1~2문장 한국어로 설명. 근거가 부족하면 '정보 부족'을 명시")


class FitAnalysisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100, description="종합 적합도 점수(0~100 정수)")
    summary: str = Field(description="종합 평가 한 줄 요약(한국어)")
    matched_skills: list[str] = Field(
        default_factory=list,
        description="이력서 skills 목록에 실제로 존재하며 공고 요건과 관련된 스킬만",
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="공고의 자격요건·우대사항이 요구하지만 이력서에서 확인되지 않는 스킬",
    )
    skill: FitDimension = Field(description="기술 스택 적합도")
    career: FitDimension = Field(description="경력 적합도")
    education: FitDimension = Field(description="학력/자격 적합도")
    strengths: list[str] = Field(default_factory=list, description="지원 시 강점 3~5개(한국어)")
    gaps: list[str] = Field(default_factory=list, description="보완할 점/개선 제안 3~5개(한국어)")


class InterviewQuestionAnswer(BaseModel):
    question: str = Field(description="면접에서 받을 수 있는 질문(한국어)")
    answer: str = Field(description="이력서와 분석 결과에서 확인 가능한 사실에 기반한 답변 예시(한국어)")
    intent: str = Field(description="면접관이 이 질문으로 확인하려는 평가 의도")
    source: str = Field(description="matched_skills, gaps, strengths, career 등 질문 근거")


class InterviewPreparationResult(BaseModel):
    summary: str = Field(description="이 분석 결과를 기준으로 한 면접 준비 방향 요약(한국어)")
    general_questions: list[InterviewQuestionAnswer] = Field(
        min_length=1,
        description="인성, 협업, 지원동기, 회사/직무 이해도 등 직무와 무관하게 범용적인 면접 질문과 답변",
    )
    professional_questions: list[InterviewQuestionAnswer] = Field(
        min_length=1,
        description="개발자, 디자이너 등 전문 직무 역량을 검증하는 질문과 답변",
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_questions(cls, data):
        """기존 캐시의 flat questions 필드를 새 직무 질문 그룹으로 읽는다."""
        if not isinstance(data, dict):
            return data
        if "questions" not in data:
            return data
        migrated = dict(data)
        questions = migrated.pop("questions")
        migrated.setdefault(
            "general_questions",
            [
                {
                    "question": "지원 동기와 협업 경험을 설명해주세요.",
                    "answer": "이력서와 채용공고에서 확인 가능한 경험을 바탕으로 지원 동기와 협업 방식을 연결해 답변합니다.",
                    "intent": "지원동기와 커뮤니케이션 방식 확인",
                    "source": "legacy_questions",
                }
            ],
        )
        migrated.setdefault("professional_questions", questions)
        return migrated


class AnalysisCreateRequest(BaseModel):
    resume_document_id: int
    job_posting_document_id: int


class AnalysisAccepted(BaseModel):
    analysis_id: int


class AnalysisStatus(BaseModel):
    analysis_id: int
    status: ParseStatus
    result: FitAnalysisResult | None = None
    error: str | None = None


class AnalysisListItem(BaseModel):
    analysis_id: int
    status: ParseStatus
    overall_score: int | None = None
    resume_title: str | None = None
    resume_name: str | None = None
    company_name: str | None = None
    job_posting_title: str | None = None
    created_at: datetime
