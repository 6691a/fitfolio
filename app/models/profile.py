from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class ResumeProfile(BaseModel):
    __tablename__ = "resume_profiles"

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    self_introduction: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_experiences: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    raw_sections: Mapped[dict] = mapped_column(JSON, default=dict)


class JobPostingProfile(BaseModel):
    __tablename__ = "job_posting_profiles"

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    career_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_period: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    qualifications: Mapped[list] = mapped_column(JSON, default=list)
    preferred_qualifications: Mapped[list] = mapped_column(JSON, default=list)
    benefits: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    raw_sections: Mapped[dict] = mapped_column(JSON, default=dict)
