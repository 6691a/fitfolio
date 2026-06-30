"""검색 텍스트가 비어 있는 기존 채용공고 프로필의 search_text(pg_trgm 검색용)를 채운다.

실행: uv run python scripts/backfill_job_posting_search_index.py
"""

import asyncio

from app.database.session import Database
from app.repositories.profiles import ProfilesRepository
from app.schemas.profiles import JobPostingProfileData
from app.services.profiles import build_job_posting_search_text


def _to_profile_data(row) -> JobPostingProfileData:
    """백필용으로 ORM 행을 검색 텍스트 합성에 필요한 DTO로 변환한다."""
    return JobPostingProfileData(
        document_text=row.document_text or "",
        company_name=row.company_name,
        title=row.title,
        location=row.location,
        employment_type=row.employment_type,
        career_requirement=row.career_requirement,
        education_requirement=row.education_requirement,
        responsibilities=row.responsibilities or [],
        qualifications=row.qualifications or [],
        preferred_qualifications=row.preferred_qualifications or [],
        benefits=row.benefits or [],
    )


async def main() -> None:
    """search_text가 없는 채용공고에 search_text를 채운다."""
    async with Database() as database:
        repo = ProfilesRepository(session_factory=database.async_session)
        rows = await repo.list_job_postings_without_search_text()
        print(f"백필 대상: {len(rows)}건")

        for row in rows:
            search_text = build_job_posting_search_text(_to_profile_data(row))
            await repo.set_job_posting_search_text(document_id=row.document_id, search_text=search_text)
            print(f"  document_id={row.document_id}: 완료")

        print(f"백필 완료: {len(rows)}건")


if __name__ == "__main__":
    asyncio.run(main())
