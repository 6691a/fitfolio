from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import app.tasks.analyses as tasks_module
from app.ai.extraction.errors import StructuredExtractionError
from app.schemas.analyses import FitAnalysisResult, FitDimension, InterviewPreparationResult
from app.schemas.documents import ParseStatus
from app.services.analysis import AnalysisService
from app.services.errors import AnalysisNotReadyError, ProfileNotReadyError, ResumeNotFoundError


def _resume_profile(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        title="백엔드 개발자 이력서",
        career_summary="백엔드 3년",
        work_experiences=[],
        projects=[],
        skills=["Python", "FastAPI"],
        education=[],
        certifications=[],
    )


def _job_posting_profile() -> SimpleNamespace:
    return SimpleNamespace(
        company_name="회사",
        title="백엔드 개발자",
        career_requirement="3년 이상",
        education_requirement="학력 무관",
        responsibilities=["API 개발"],
        qualifications=["Python"],
        preferred_qualifications=["Kubernetes"],
    )


def _fit_result() -> FitAnalysisResult:
    return FitAnalysisResult(
        overall_score=80,
        summary="적합",
        matched_skills=["Python"],
        missing_skills=["Kubernetes"],
        skill=FitDimension(score=85, comment="기술 일치"),
        career=FitDimension(score=75, comment="경력 충족"),
        education=FitDimension(score=70, comment="정보 부족"),
        strengths=["Python 실무 경험"],
        gaps=["Kubernetes 경험 보완"],
    )


def _interview_result() -> InterviewPreparationResult:
    return InterviewPreparationResult(
        summary="기술 강점은 살리고 Kubernetes 공백은 보완한다.",
        general_questions=[
            {
                "question": "지원 동기를 설명해주세요.",
                "answer": "채용공고의 역할과 본인의 백엔드 경험을 연결해 답변합니다.",
                "intent": "지원동기와 직무 이해도 확인",
                "source": "job_posting",
            }
        ],
        professional_questions=[
            {
                "question": "FastAPI로 API를 설계할 때 가장 중요하게 본 점은 무엇인가요?",
                "answer": "이력서에 있는 Python/FastAPI 경험을 기준으로 응답 구조와 예외 처리를 설명합니다.",
                "intent": "실무 설계 역량 확인",
                "source": "matched_skills",
            }
        ],
    )


class FakeProfilesRepository:
    def __init__(self, resumes: dict | None = None, job_postings: dict | None = None) -> None:
        self.resumes = resumes or {}
        self.job_postings = job_postings or {}

    async def get_resume_profile(self, *, document_id: int):
        return self.resumes.get(document_id)

    async def get_job_posting_profile(self, *, document_id: int):
        return self.job_postings.get(document_id)


class FakePreferencesRepository:
    def __init__(self, preferences: dict | None = None) -> None:
        self.preferences = preferences or {}

    async def get_by_user(self, user_id: int):
        return self.preferences.get(user_id)


class FakeUserProfilesRepository:
    def __init__(self) -> None:
        self.profiles: dict[int, SimpleNamespace] = {}

    async def get_by_user(self, user_id: int):
        return self.profiles.get(user_id)

    async def upsert(self, user_id: int, **values):
        self.profiles[user_id] = SimpleNamespace(user_id=user_id, **values)
        return self.profiles[user_id]


def _service(analyses, profiles, preferences=None, user_profiles=None) -> AnalysisService:
    return AnalysisService(
        analyses,  # type: ignore[arg-type]
        profiles,  # type: ignore[arg-type]
        preferences or FakePreferencesRepository(),  # type: ignore[arg-type]
        user_profiles or FakeUserProfilesRepository(),  # type: ignore[arg-type]
    )


class FakeAnalysesRepository:
    def __init__(self) -> None:
        self.records: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    async def create(self, *, user_id: int, resume_document_id: int, job_posting_document_id: int):
        record = SimpleNamespace(
            id=self._next_id,
            user_id=user_id,
            resume_document_id=resume_document_id,
            job_posting_document_id=job_posting_document_id,
            status=ParseStatus.PENDING,
            result=None,
            interview_preparation=None,
            error=None,
            deleted_at=None,
        )
        self.records[record.id] = record
        self._next_id += 1
        return record

    async def get(self, analysis_id: int):
        record = self.records.get(analysis_id)
        if record is None or record.deleted_at is not None:
            return None
        return record

    async def soft_delete(self, analysis_id: int, *, user_id: int) -> bool:
        record = self.records.get(analysis_id)
        if record is None or record.user_id != user_id or record.deleted_at is not None:
            return False
        record.deleted_at = datetime(2026, 7, 3, tzinfo=UTC)
        return True

    async def mark_started(self, analysis_id: int) -> None:
        self.records[analysis_id].status = ParseStatus.STARTED

    async def mark_done(self, analysis_id: int, *, result: dict) -> None:
        record = self.records[analysis_id]
        record.status = ParseStatus.DONE
        record.result = result

    async def save_interview_preparation(self, analysis_id: int, *, interview_preparation: dict) -> None:
        self.records[analysis_id].interview_preparation = interview_preparation

    async def mark_failed(self, analysis_id: int, *, error: str) -> None:
        record = self.records[analysis_id]
        record.status = ParseStatus.FAILED
        record.error = error

    async def list_by_user(self, *, user_id: int, limit: int = 50):
        return [
            (record, "이력서 제목", "홍길동", "회사", "백엔드 개발자")
            for record in reversed(self.records.values())
            if record.user_id == user_id and record.deleted_at is None
        ][:limit]

    async def save_feedback(self, analysis_id: int, *, user_id: int, feedback: dict) -> bool:
        record = self.records.get(analysis_id)
        if record is None or record.user_id != user_id or record.status != ParseStatus.DONE:
            return False
        record.feedback = feedback
        return True

    async def list_recent_feedback(self, user_id: int, *, limit: int = 5) -> list[dict]:
        return [
            record.feedback
            for record in reversed(self.records.values())
            if record.user_id == user_id and getattr(record, "feedback", None)
        ][:limit]

    async def list_recent_analyzed_profiles(self, user_id: int, *, limit: int = 30):
        return []


@pytest.mark.asyncio
async def test_request_analysis_creates_pending_and_enqueues_task(monkeypatch):
    analyses = FakeAnalysesRepository()
    profiles = FakeProfilesRepository(resumes={11: _resume_profile()}, job_postings={22: _job_posting_profile()})
    delayed_ids = []
    monkeypatch.setattr(tasks_module.task_analyze_fit, "delay", lambda analysis_id: delayed_ids.append(analysis_id))

    accepted = await _service(analyses, profiles).request_analysis(
        user_id=1, resume_document_id=11, job_posting_document_id=22
    )

    assert accepted.analysis_id == 1
    assert analyses.records[1].status == ParseStatus.PENDING
    assert delayed_ids == [1]


@pytest.mark.asyncio
async def test_request_analysis_rejects_unparsed_resume():
    service = _service(FakeAnalysesRepository(), FakeProfilesRepository())

    with pytest.raises(ProfileNotReadyError):
        await service.request_analysis(user_id=1, resume_document_id=11, job_posting_document_id=22)


@pytest.mark.asyncio
async def test_request_analysis_rejects_other_users_resume():
    profiles = FakeProfilesRepository(resumes={11: _resume_profile(user_id=2)})
    service = _service(FakeAnalysesRepository(), profiles)

    with pytest.raises(ResumeNotFoundError):
        await service.request_analysis(user_id=1, resume_document_id=11, job_posting_document_id=22)


@pytest.mark.asyncio
async def test_request_analysis_rejects_unparsed_job_posting():
    profiles = FakeProfilesRepository(resumes={11: _resume_profile()})
    service = _service(FakeAnalysesRepository(), profiles)

    with pytest.raises(ProfileNotReadyError):
        await service.request_analysis(user_id=1, resume_document_id=11, job_posting_document_id=22)


@pytest.mark.asyncio
async def test_run_saves_result_on_success(monkeypatch):
    analyses = FakeAnalysesRepository()
    profiles = FakeProfilesRepository(resumes={11: _resume_profile()}, job_postings={22: _job_posting_profile()})
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)

    async def fake_analyze_fit(resume, job_posting, *, user_context=""):
        assert resume["skills"] == ["Python", "FastAPI"]
        assert job_posting["qualifications"] == ["Python"]
        return _fit_result()

    monkeypatch.setattr("app.ai.graph.analysis.analyze_fit", fake_analyze_fit)

    await _service(analyses, profiles).run(1)

    record = analyses.records[1]
    assert record.status == ParseStatus.DONE
    assert record.result["overall_score"] == 80


@pytest.mark.asyncio
async def test_run_marks_failed_when_llm_raises(monkeypatch):
    analyses = FakeAnalysesRepository()
    profiles = FakeProfilesRepository(resumes={11: _resume_profile()}, job_postings={22: _job_posting_profile()})
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)

    async def fake_analyze_fit(resume, job_posting, *, user_context=""):
        raise StructuredExtractionError("boom")

    monkeypatch.setattr("app.ai.graph.analysis.analyze_fit", fake_analyze_fit)

    await _service(analyses, profiles).run(1)

    record = analyses.records[1]
    assert record.status == ParseStatus.FAILED
    assert "boom" in record.error


@pytest.mark.asyncio
async def test_run_marks_failed_when_profile_deleted():
    analyses = FakeAnalysesRepository()
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)

    await _service(analyses, FakeProfilesRepository()).run(1)

    assert analyses.records[1].status == ParseStatus.FAILED


@pytest.mark.asyncio
async def test_refresh_user_profile_upserts_from_recent_analyses():
    analyses = FakeAnalysesRepository()

    async def list_recent(user_id, *, limit=30):
        assert user_id == 1
        return [
            (SimpleNamespace(domain="백엔드", tech_tags=["Python"], title=None), _resume_profile()),
        ]

    analyses.list_recent_analyzed_profiles = list_recent  # type: ignore[method-assign]
    user_profiles = FakeUserProfilesRepository()

    await _service(analyses, FakeProfilesRepository(), user_profiles=user_profiles).refresh_user_profile(1)

    stored = user_profiles.profiles[1]
    assert stored.interest_domains == ["백엔드"]
    assert stored.interest_tech == ["Python"]
    assert stored.own_skills == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_refresh_user_profile_is_fail_soft_on_error():
    analyses = FakeAnalysesRepository()

    async def boom(user_id, *, limit=30):
        raise RuntimeError("db down")

    analyses.list_recent_analyzed_profiles = boom  # type: ignore[method-assign]

    # 예외를 삼키지 않고 로깅하되, 호출자에게 전파하지 않는다(분석 완료 유지).
    await _service(analyses, FakeProfilesRepository()).refresh_user_profile(1)


@pytest.mark.asyncio
async def test_list_analyses_returns_own_items_with_score():
    analyses = FakeAnalysesRepository()
    done = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    done.status = ParseStatus.DONE
    done.created_at = datetime(2026, 7, 3, tzinfo=UTC)
    done.result = _fit_result().model_dump(mode="json")
    pending = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=33)
    pending.created_at = datetime(2026, 7, 3, tzinfo=UTC)
    other = await analyses.create(user_id=2, resume_document_id=99, job_posting_document_id=22)
    other.created_at = datetime(2026, 7, 3, tzinfo=UTC)

    items = await _service(analyses, FakeProfilesRepository()).list_analyses(user_id=1)

    assert [item.analysis_id for item in items] == [2, 1]
    assert items[0].overall_score is None
    assert items[1].overall_score == 80
    assert items[1].company_name == "회사"


@pytest.mark.asyncio
async def test_get_analysis_restores_result_and_hides_other_users():
    analyses = FakeAnalysesRepository()
    record = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    record.status = ParseStatus.DONE
    record.result = _fit_result().model_dump(mode="json")
    service = _service(analyses, FakeProfilesRepository())

    mine = await service.get_analysis(analysis_id=1, user_id=1)
    assert mine is not None
    assert mine.status == ParseStatus.DONE
    assert mine.result is not None
    assert mine.result.overall_score == 80

    assert await service.get_analysis(analysis_id=1, user_id=2) is None
    assert await service.get_analysis(analysis_id=999, user_id=1) is None


@pytest.mark.asyncio
async def test_delete_analysis_soft_deletes_and_hides_from_queries():
    analyses = FakeAnalysesRepository()
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    service = _service(analyses, FakeProfilesRepository())

    assert await service.delete_analysis(analysis_id=1, user_id=1) is True
    assert analyses.records[1].deleted_at is not None
    # 삭제 후에는 조회·목록에서 사라진다.
    assert await service.get_analysis(analysis_id=1, user_id=1) is None
    assert await service.list_analyses(user_id=1) == []


@pytest.mark.asyncio
async def test_delete_analysis_rejects_missing_and_other_users():
    analyses = FakeAnalysesRepository()
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    service = _service(analyses, FakeProfilesRepository())

    assert await service.delete_analysis(analysis_id=1, user_id=2) is False
    assert await service.delete_analysis(analysis_id=999, user_id=1) is False
    assert analyses.records[1].deleted_at is None


@pytest.mark.asyncio
async def test_prepare_interview_returns_cached_result_without_regeneration():
    analyses = FakeAnalysesRepository()
    record = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    record.status = ParseStatus.DONE
    record.result = _fit_result().model_dump(mode="json")
    record.interview_preparation = _interview_result().model_dump(mode="json")

    result = await _service(analyses, FakeProfilesRepository()).prepare_interview(analysis_id=1, user_id=1)

    assert result == _interview_result()


@pytest.mark.asyncio
async def test_prepare_interview_generates_and_persists_when_missing(monkeypatch):
    analyses = FakeAnalysesRepository()
    record = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    record.status = ParseStatus.DONE
    record.result = _fit_result().model_dump(mode="json")
    profiles = FakeProfilesRepository(resumes={11: _resume_profile()}, job_postings={22: _job_posting_profile()})

    async def fake_generate(service, *, analysis_id):
        assert analysis_id == 1
        return {"interview_preparation": _interview_result()}

    monkeypatch.setattr("app.ai.graph.analysis.run_interview_preparation_graph", fake_generate)

    result = await _service(analyses, profiles).prepare_interview(analysis_id=1, user_id=1)

    assert result == _interview_result()
    assert analyses.records[1].interview_preparation == _interview_result().model_dump(mode="json")


@pytest.mark.asyncio
async def test_prepare_interview_rejects_unfinished_analysis():
    analyses = FakeAnalysesRepository()
    await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)

    with pytest.raises(AnalysisNotReadyError):
        await _service(analyses, FakeProfilesRepository()).prepare_interview(analysis_id=1, user_id=1)


@pytest.mark.asyncio
async def test_prepare_interview_hides_other_users_analysis():
    analyses = FakeAnalysesRepository()
    record = await analyses.create(user_id=1, resume_document_id=11, job_posting_document_id=22)
    record.status = ParseStatus.DONE
    record.result = _fit_result().model_dump(mode="json")

    assert await _service(analyses, FakeProfilesRepository()).prepare_interview(analysis_id=1, user_id=2) is None
