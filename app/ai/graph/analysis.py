import logging
from collections.abc import Mapping
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.ai.analysis import analyze_fit, job_posting_fit_input, resume_fit_input, select_best_position
from app.ai.interview import generate_interview_preparation
from app.ai.memory import build_user_context
from app.schemas.analyses import FitAnalysisResult
from app.schemas.documents import ParseStatus
from app.ai.graph.state import AnalysisGraphState, AnalysisNextSkill

logger = logging.getLogger(__name__)

_FIT_ANALYSIS_SKILLS = {"load_profiles", "evaluate_fit", "persist_done", "persist_failed", "finish"}
_INTERVIEW_PREPARATION_SKILLS = {
    "load_profiles",
    "prepare_interview",
    "persist_interview_preparation",
    "finish",
}


async def load_user_context(service: Any, user_id: int) -> str:
    """저장된 관심사·물질화된 집계 프로필·최근 피드백을 합쳐 프롬프트용 컨텍스트 블록을 만든다.

    관심 직무·기술은 저장값(사용자 수정본) 우선, 없으면 물질화된 UserProfile 집계값을 쓴다.
    즉석 재계산 대신 저장된 프로필을 읽는다(집계는 분석 완료 시 upsert된다). 개인화는 fail-soft다:
    조회에 실패해도 분석 자체는 막지 않되, 원인은 반드시 로깅한다.

    Args:
        service: AnalysisService 인스턴스(_preferences/_user_profiles/_analyses 보유).
        user_id: 컨텍스트를 만들 사용자 ID.

    Returns:
        렌더된 개인화 컨텍스트 블록, 없거나 실패하면 빈 문자열.
    """
    try:
        preferences = await service._preferences.get_by_user(user_id)
        profile = await service._user_profiles.get_by_user(user_id)
        feedback = await service._analyses.list_recent_feedback(user_id, limit=5)
        return build_user_context(preferences, profile, feedback)
    except Exception as exc:
        logger.warning("개인화 컨텍스트 로드 실패, 빈 컨텍스트로 진행: user_id=%s error=%s", user_id, exc)
        return ""


def safe_analysis_route(state: Mapping[str, Any], *, allowed: set[str]) -> AnalysisNextSkill:
    """허용된 분석 스킬만 라우팅하고 나머지 작업 요청은 자동 종료한다."""
    next_skill = state.get("next_skill", "finish")
    if next_skill not in allowed:
        logger.warning("지원하지 않는 분석 그래프 작업 종료: next_skill=%s", next_skill)
        return "finish"
    return cast(AnalysisNextSkill, next_skill)


def _route_fit(state: AnalysisGraphState) -> AnalysisNextSkill:
    """적합도 분석 그래프에서 허용된 다음 스킬 이름을 반환한다."""
    return safe_analysis_route(state, allowed=_FIT_ANALYSIS_SKILLS)


def _route_interview(state: AnalysisGraphState) -> AnalysisNextSkill:
    """면접 준비 그래프에서 허용된 다음 스킬 이름을 반환한다."""
    return safe_analysis_route(state, allowed=_INTERVIEW_PREPARATION_SKILLS)


def build_analysis_graph(service: Any):
    """기존 AnalysisService 기능을 LangGraph 노드로 연결한 적합도 분석 그래프를 만든다.

    Args:
        service: AnalysisService 인스턴스. 순환 import를 피하려고 런타임 객체로 받는다.

    Returns:
        컴파일된 LangGraph 적합도 분석 그래프.
    """

    async def load_analysis(state: AnalysisGraphState) -> AnalysisGraphState:
        record = await service._analyses.get(state["analysis_id"])
        if record is None:
            logger.warning("존재하지 않는 분석 실행 요청: analysis_id=%s", state["analysis_id"])
            return {"completed": False, "next_skill": "finish"}
        await service._analyses.mark_started(state["analysis_id"])
        return {"record": record, "next_skill": "load_profiles"}

    async def load_profiles(state: AnalysisGraphState) -> AnalysisGraphState:
        record = state["record"]
        resume = await service._profiles.get_resume_profile(document_id=record.resume_document_id)
        job_posting = await service._profiles.get_job_posting_profile(document_id=record.job_posting_document_id)
        if resume is None or job_posting is None:
            logger.warning(
                "분석 대상 프로필 없음: analysis_id=%s resume=%s job_posting=%s",
                state["analysis_id"],
                record.resume_document_id,
                record.job_posting_document_id,
            )
            return {"error": "분석 대상 프로필을 찾을 수 없습니다", "next_skill": "persist_failed"}
        # 여러 모집부문 공고는 이력서에 가장 맞는 포지션만 골라 채점(다른 직무 요건이 점수를 흐리지 않게).
        position = select_best_position(getattr(job_posting, "positions", None) or [], resume.skills or [])
        return {
            "resume_profile": resume,
            "job_posting_profile": job_posting,
            "resume_input": resume_fit_input(resume),
            "job_posting_input": job_posting_fit_input(job_posting, position=position),
            "matched_position": (position or {}).get("title") if position else None,
            "user_context": await load_user_context(service, record.user_id),
            "next_skill": "evaluate_fit",
        }

    async def evaluate_fit(state: AnalysisGraphState) -> AnalysisGraphState:
        try:
            result = await analyze_fit(
                state["resume_input"],
                state["job_posting_input"],
                user_context=state.get("user_context", ""),
            )
        except Exception as exc:
            logger.exception("적합도 분석 실패: analysis_id=%s", state["analysis_id"])
            return {"error": str(exc), "next_skill": "persist_failed"}
        # 자동 선택된 포지션명은 시스템 메타데이터라 LLM 출력이 아니라 여기서 결정적으로 채운다.
        result.matched_position = state.get("matched_position")
        return {"result": result, "next_skill": "persist_done"}

    async def persist_done(state: AnalysisGraphState) -> AnalysisGraphState:
        await service._analyses.mark_done(
            state["analysis_id"],
            result=state["result"].model_dump(mode="json"),
        )
        return {"completed": True, "next_skill": "finish"}

    async def persist_failed(state: AnalysisGraphState) -> AnalysisGraphState:
        await service._analyses.mark_failed(
            state["analysis_id"],
            error=state.get("error") or "적합도 분석에 실패했습니다",
        )
        return {"completed": False, "next_skill": "finish"}

    builder = StateGraph(AnalysisGraphState)  # pyrefly: ignore [bad-specialization]
    builder.add_node("load_analysis", load_analysis)
    builder.add_node("load_profiles", load_profiles)
    builder.add_node("evaluate_fit", evaluate_fit)
    builder.add_node("persist_done", persist_done)
    builder.add_node("persist_failed", persist_failed)
    builder.add_edge(START, "load_analysis")
    builder.add_conditional_edges(
        "load_analysis",
        _route_fit,
        {
            "load_profiles": "load_profiles",
            "finish": END,
            "persist_failed": "persist_failed",
        },
    )
    builder.add_conditional_edges(
        "load_profiles",
        _route_fit,
        {
            "evaluate_fit": "evaluate_fit",
            "persist_failed": "persist_failed",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "evaluate_fit",
        _route_fit,
        {
            "persist_done": "persist_done",
            "persist_failed": "persist_failed",
            "finish": END,
        },
    )
    builder.add_edge("persist_done", END)
    builder.add_edge("persist_failed", END)
    return builder.compile(name="fit_analysis")


def build_interview_preparation_graph(service: Any):
    """완료된 적합도 분석 결과를 바탕으로 면접 준비 질문/답변 생성 그래프를 만든다.

    Args:
        service: AnalysisService 인스턴스. 순환 import를 피하려고 런타임 객체로 받는다.

    Returns:
        컴파일된 LangGraph 면접 준비 그래프.
    """

    async def load_analysis(state: AnalysisGraphState) -> AnalysisGraphState:
        record = await service._analyses.get(state["analysis_id"])
        if record is None:
            logger.warning("존재하지 않는 면접 준비 요청: analysis_id=%s", state["analysis_id"])
            return {"completed": False, "next_skill": "finish"}
        if record.status != ParseStatus.DONE or not record.result:
            logger.info("완료되지 않은 분석의 면접 준비 요청 종료: analysis_id=%s", state["analysis_id"])
            return {
                "completed": False,
                "error": "완료된 분석에서만 면접 질문을 만들 수 있습니다",
                "next_skill": "finish",
            }
        return {
            "record": record,
            "analysis_result": FitAnalysisResult.model_validate(record.result),
            "next_skill": "load_profiles",
        }

    async def load_profiles(state: AnalysisGraphState) -> AnalysisGraphState:
        record = state["record"]
        resume = await service._profiles.get_resume_profile(document_id=record.resume_document_id)
        job_posting = await service._profiles.get_job_posting_profile(document_id=record.job_posting_document_id)
        if resume is None or job_posting is None:
            logger.warning(
                "면접 준비 대상 프로필 없음: analysis_id=%s resume=%s job_posting=%s",
                state["analysis_id"],
                record.resume_document_id,
                record.job_posting_document_id,
            )
            return {"completed": False, "error": "분석 대상 프로필을 찾을 수 없습니다", "next_skill": "finish"}
        # 적합도 분석과 동일하게 이력서에 맞는 포지션 기준으로 면접 질문을 만든다.
        position = select_best_position(getattr(job_posting, "positions", None) or [], resume.skills or [])
        return {
            "resume_profile": resume,
            "job_posting_profile": job_posting,
            "resume_input": resume_fit_input(resume),
            "job_posting_input": job_posting_fit_input(job_posting, position=position),
            "matched_position": (position or {}).get("title") if position else None,
            "user_context": await load_user_context(service, record.user_id),
            "next_skill": "prepare_interview",
        }

    async def prepare_interview(state: AnalysisGraphState) -> AnalysisGraphState:
        try:
            result = await generate_interview_preparation(
                resume=state["resume_input"],
                job_posting=state["job_posting_input"],
                analysis_result=state["analysis_result"],
                user_context=state.get("user_context", ""),
            )
        except Exception as exc:
            logger.exception("면접 준비 생성 실패: analysis_id=%s", state["analysis_id"])
            return {"completed": False, "error": str(exc), "next_skill": "finish"}
        return {"interview_preparation": result, "next_skill": "persist_interview_preparation"}

    async def persist_interview_preparation(state: AnalysisGraphState) -> AnalysisGraphState:
        await service._analyses.save_interview_preparation(
            state["analysis_id"],
            interview_preparation=state["interview_preparation"].model_dump(mode="json"),
        )
        return {"completed": True, "next_skill": "finish"}

    builder = StateGraph(AnalysisGraphState)  # pyrefly: ignore [bad-specialization]
    builder.add_node("load_analysis", load_analysis)
    builder.add_node("load_profiles", load_profiles)
    builder.add_node("prepare_interview", prepare_interview)
    builder.add_node("persist_interview_preparation", persist_interview_preparation)
    builder.add_edge(START, "load_analysis")
    builder.add_conditional_edges(
        "load_analysis",
        _route_interview,
        {
            "load_profiles": "load_profiles",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "load_profiles",
        _route_interview,
        {
            "prepare_interview": "prepare_interview",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "prepare_interview",
        _route_interview,
        {
            "persist_interview_preparation": "persist_interview_preparation",
            "finish": END,
        },
    )
    builder.add_edge("persist_interview_preparation", END)
    return builder.compile(name="interview_preparation")


async def run_analysis_graph(service: Any, *, analysis_id: int) -> AnalysisGraphState:
    """적합도 분석 그래프를 실행한다.

    Args:
        service: AnalysisService 인스턴스.
        analysis_id: 실행할 분석 ID.

    Returns:
        최종 LangGraph state.
    """
    graph = build_analysis_graph(service)
    state = await graph.ainvoke({"analysis_id": analysis_id})
    return cast(AnalysisGraphState, state)


async def run_interview_preparation_graph(service: Any, *, analysis_id: int) -> AnalysisGraphState:
    """면접 준비 그래프를 실행한다.

    Args:
        service: AnalysisService 인스턴스.
        analysis_id: 면접 준비를 생성할 완료 분석 ID.

    Returns:
        최종 LangGraph state.
    """
    graph = build_interview_preparation_graph(service)
    state = await graph.ainvoke({"analysis_id": analysis_id})
    return cast(AnalysisGraphState, state)
