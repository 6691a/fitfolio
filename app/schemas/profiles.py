from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.config.settings import settings
from app.schemas.documents import EmploymentType, Region
from app.utils import serialize_datetime_in_timezone


class ResumeProfileData(BaseModel):
    document_text: str
    image_text: str = ""
    title: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    self_introduction: str | None = None
    career_summary: str | None = None
    work_experiences: list[dict | str] = Field(default_factory=list)
    projects: list[dict | str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[dict | str] = Field(default_factory=list)
    certifications: list[dict | str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    etc: list[dict | str] = Field(default_factory=list)
    raw_sections: dict = Field(default_factory=dict)


class JobPostingProfileData(BaseModel):
    document_text: str
    image_text: str = ""
    company_name: str | None = None
    title: str | None = None
    location: str | None = None
    region: Region | None = None
    employment_type: EmploymentType | None = None
    career_requirement: str | None = None
    education_requirement: str | None = None
    domain: str | None = None
    tech_tags: list[str] = Field(default_factory=list)
    start_date: datetime | None = None
    end_date: datetime | None = None
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    positions: list[dict] = Field(default_factory=list)
    source_url: str | None = None
    raw_sections: dict = Field(default_factory=dict)

    @field_serializer("start_date", "end_date", when_used="json")
    def serialize_response_datetime(self, value: datetime | None) -> str | None:
        """API 응답에서는 설정 timezone으로 변환해 직렬화한다.

        DB 저장 경로의 `model_dump()`는 python mode라 UTC datetime을 그대로 유지한다.
        """
        return serialize_datetime_in_timezone(value, timezone=settings.TIME_ZONE)


ProfileData = ResumeProfileData | JobPostingProfileData


class ResumeListItem(BaseModel):
    document_id: int
    title: str | None = None
    name: str | None = None
    email: str | None = None
    career_summary: str | None = None
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_response_datetime(self, value: datetime) -> str | None:
        """API 응답에서는 설정 timezone으로 변환해 직렬화한다."""
        return serialize_datetime_in_timezone(value, timezone=settings.TIME_ZONE)


class JobPostingListItem(BaseModel):
    document_id: int
    company_name: str | None = None
    title: str | None = None
    location: str | None = None
    region: Region | None = None
    employment_type: EmploymentType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    source_url: str | None = None
    score: float | None = None  # 검색어가 있을 때만 채워지는 관련도 점수

    @field_serializer("start_date", "end_date", when_used="json")
    def serialize_response_datetime(self, value: datetime | None) -> str | None:
        """API 응답에서는 설정 timezone으로 변환해 직렬화한다."""
        return serialize_datetime_in_timezone(value, timezone=settings.TIME_ZONE)
