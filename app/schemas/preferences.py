from pydantic import BaseModel, ConfigDict, Field


class PreferencesUpdate(BaseModel):
    interest_jobs: str | None = Field(default=None, max_length=2000, description="관심 직무(사용자 수정본)")
    interest_skills: str | None = Field(default=None, max_length=2000, description="관심 기술/역량(사용자 수정본)")
    notes: str | None = Field(default=None, max_length=2000, description="강조점·답변 톤 등 자유 메모")


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interest_jobs: str | None = None
    interest_skills: str | None = None
    notes: str | None = None
    # 최근 분석에서 자동 추출한 제안값(읽기 전용). 저장값이 비었을 때 폼/프롬프트가 대신 쓴다.
    suggested_jobs: str | None = None
    suggested_skills: str | None = None
