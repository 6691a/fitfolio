from typing import Any, Literal, TypedDict

from app.schemas.analyses import FitAnalysisResult, InterviewPreparationResult
from app.schemas.documents import DocumentClassification, DocumentInput, ParsedDocument

DocumentNextSkill = Literal[
    "parse_document",
    "classify_document",
    "persist_done",
    "persist_failed",
    "finish",
]

AnalysisNextSkill = Literal[
    "load_profiles",
    "evaluate_fit",
    "prepare_interview",
    "persist_interview_preparation",
    "persist_done",
    "persist_failed",
    "finish",
]


class DocumentGraphState(TypedDict, total=False):
    document_id: int
    user_id: int
    document: Any
    document_input: DocumentInput
    parsed: ParsedDocument
    classification: DocumentClassification
    next_skill: DocumentNextSkill
    error: str
    completed: bool


class AnalysisGraphState(TypedDict, total=False):
    analysis_id: int
    record: Any
    resume_profile: Any
    job_posting_profile: Any
    resume_input: dict
    job_posting_input: dict
    result: FitAnalysisResult
    analysis_result: FitAnalysisResult
    interview_preparation: InterviewPreparationResult
    next_skill: AnalysisNextSkill
    error: str
    completed: bool
