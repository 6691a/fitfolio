from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.ai.graph.analysis import run_analysis_graph, run_interview_preparation_graph, safe_analysis_route
from app.schemas.analyses import FitAnalysisResult, FitDimension, InterviewPreparationResult
from app.schemas.documents import ParseStatus


def _fit_result() -> FitAnalysisResult:
    return FitAnalysisResult(
        overall_score=82,
        summary="적합",
        matched_skills=["Python"],
        missing_skills=["Kubernetes"],
        skill=FitDimension(score=85, comment="기술 일치"),
        career=FitDimension(score=80, comment="경력 충족"),
        education=FitDimension(score=70, comment="정보 부족"),
        strengths=["Python 경험"],
        gaps=["Kubernetes 보완"],
    )


def _interview_result() -> InterviewPreparationResult:
    return InterviewPreparationResult(
        summary="부족 기술 보완 중심으로 준비한다.",
        general_questions=[
            {
                "question": "입사 후 어떤 방식으로 팀에 기여하고 싶나요?",
                "answer": "Python 백엔드 경험을 바탕으로 API 개발과 협업 기여 방향을 답변합니다.",
                "intent": "협업 태도와 회사 적응력 확인",
                "source": "strengths",
            }
        ],
        professional_questions=[
            {
                "question": "Kubernetes 경험이 부족한데 어떻게 보완하고 있나요?",
                "answer": "이력서에 없는 경험을 지어내지 않고 학습 계획과 관련 경험을 연결해 답변합니다.",
                "intent": "gaps 검증",
                "source": "gaps",
            }
        ],
    )


class FakeAnalysesRepository:
    def __init__(self) -> None:
        self.record = SimpleNamespace(
            id=3,
            user_id=1,
            resume_document_id=11,
            job_posting_document_id=22,
            status=ParseStatus.PENDING,
            result=None,
            interview_preparation=None,
            error=None,
            created_at=datetime(2026, 7, 3, tzinfo=UTC),
        )
        self.started: list[int] = []
        self.done: list[tuple[int, dict]] = []
        self.failed: list[tuple[int, str]] = []

    async def get(self, analysis_id: int):
        assert analysis_id == 3
        return self.record

    async def mark_started(self, analysis_id: int) -> None:
        self.started.append(analysis_id)
        self.record.status = ParseStatus.STARTED

    async def mark_done(self, analysis_id: int, *, result: dict) -> None:
        self.done.append((analysis_id, result))
        self.record.status = ParseStatus.DONE
        self.record.result = result

    async def save_interview_preparation(self, analysis_id: int, *, interview_preparation: dict) -> None:
        assert analysis_id == 3
        self.record.interview_preparation = interview_preparation

    async def mark_failed(self, analysis_id: int, *, error: str) -> None:
        self.failed.append((analysis_id, error))
        self.record.status = ParseStatus.FAILED
        self.record.error = error


class FakeProfilesRepository:
    async def get_resume_profile(self, *, document_id: int):
        assert document_id == 11
        return SimpleNamespace(
            title="백엔드 개발자 이력서",
            career_summary="백엔드 3년",
            work_experiences=[],
            projects=[],
            skills=["Python"],
            education=[],
            certifications=[],
        )

    async def get_job_posting_profile(self, *, document_id: int):
        assert document_id == 22
        return SimpleNamespace(
            company_name="회사",
            title="백엔드 개발자",
            career_requirement="3년 이상",
            education_requirement="학력 무관",
            responsibilities=["API 개발"],
            qualifications=["Python"],
            preferred_qualifications=["Kubernetes"],
        )


class FakeAnalysisService:
    """그래프가 쓰는 것은 repo 두 개뿐이다. LLM 호출은 모듈 함수 monkeypatch로 대체한다."""

    def __init__(self) -> None:
        self._analyses = FakeAnalysesRepository()
        self._profiles = FakeProfilesRepository()


@pytest.mark.asyncio
async def test_analysis_graph_runs_profile_lookup_evaluation_and_persist_skills(monkeypatch):
    service = FakeAnalysisService()

    async def fake_analyze_fit(resume, job_posting):
        assert resume["skills"] == ["Python"]
        assert job_posting["qualifications"] == ["Python"]
        return _fit_result()

    monkeypatch.setattr("app.ai.graph.analysis.analyze_fit", fake_analyze_fit)

    state = await run_analysis_graph(service, analysis_id=3)

    assert service._analyses.started == [3]
    assert service._analyses.done == [(3, _fit_result().model_dump(mode="json"))]
    assert service._analyses.failed == []
    assert state["completed"] is True
    assert state["next_skill"] == "finish"


@pytest.mark.asyncio
async def test_interview_preparation_graph_generates_and_persists_questions(monkeypatch):
    service = FakeAnalysisService()
    service._analyses.record.status = ParseStatus.DONE
    service._analyses.record.result = _fit_result().model_dump(mode="json")

    async def fake_generate(*, resume, job_posting, analysis_result):
        assert resume["skills"] == ["Python"]
        assert job_posting["qualifications"] == ["Python"]
        assert analysis_result.overall_score == 82
        return _interview_result()

    monkeypatch.setattr("app.ai.graph.analysis.generate_interview_preparation", fake_generate)

    state = await run_interview_preparation_graph(service, analysis_id=3)

    assert state["interview_preparation"] == _interview_result()
    assert service._analyses.record.interview_preparation == _interview_result().model_dump(mode="json")
    assert state["completed"] is True


def test_analysis_graph_unknown_skill_routes_to_finish():
    assert safe_analysis_route({"next_skill": "delete_everything"}, allowed={"finish"}) == "finish"
