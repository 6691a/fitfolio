from pydantic import BaseModel, Field


class ResumeProfileData(BaseModel):
    raw_text: str
    self_introduction: str | None = None
    career_summary: str | None = None
    work_experiences: list[dict | str] = Field(default_factory=list)
    projects: list[dict | str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[dict | str] = Field(default_factory=list)
    certifications: list[dict | str] = Field(default_factory=list)
    raw_sections: dict = Field(default_factory=dict)


class JobPostingProfileData(BaseModel):
    raw_text: str
    company_name: str | None = None
    title: str | None = None
    location: str | None = None
    employment_type: str | None = None
    career_requirement: str | None = None
    education_requirement: str | None = None
    opening_period: str | None = None
    deadline: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    source_url: str | None = None
    raw_sections: dict = Field(default_factory=dict)


ProfileData = ResumeProfileData | JobPostingProfileData
