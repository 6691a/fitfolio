from app.schemas.documents import DocumentKind, ParsedDocument
from app.schemas.profiles import JobPostingProfileData, ProfileData, ResumeProfileData


class UnsupportedProfileTypeError(Exception):
    pass


def build_profile_data(document_type: DocumentKind, parsed: ParsedDocument) -> ProfileData:
    kind = DocumentKind(document_type)
    if kind == DocumentKind.RESUME:
        return ResumeProfileData(raw_text=parsed.extracted_text)

    if kind == DocumentKind.JOB_POSTING:
        return JobPostingProfileData(
            raw_text=parsed.extracted_text,
            source_url=parsed.metadata.get("source_url"),
        )

    raise UnsupportedProfileTypeError(f"Unsupported document type: {document_type}")
