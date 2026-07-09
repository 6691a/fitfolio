from datetime import UTC, datetime
from types import SimpleNamespace

from app.schemas.documents import DocumentFormat
from streamlit_app.views import analyze


class FakeButtonSlot:
    def __init__(self) -> None:
        self.calls = []

    def button(self, label, *, type=None, disabled=False):  # noqa: A002
        self.calls.append({"label": label, "type": type, "disabled": disabled})
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state = {
            "is_analyzing": True,
            "analysis_ids": {
                "resume": 11,
                "job_posting": 22,
            },
        }
        self.button_slot = FakeButtonSlot()

    def caption(self, _text):
        return None

    def error(self, _text):
        return None

    def info(self, _text):
        return None

    def selectbox(self, _label, options):
        return options[0]

    def radio(self, _label, _options, **_kwargs):
        return DocumentFormat.URL

    def text_input(self, _label):
        return "https://www.wanted.co.kr/wd/123"

    def file_uploader(self, *_args, **_kwargs):
        return None

    def empty(self):
        return self.button_slot


def test_analyze_start_button_stays_disabled_while_analysis_result_is_loading(monkeypatch):
    fake_st = FakeStreamlit()
    rendered_results = []
    resume = SimpleNamespace(
        document_id=11,
        title="백엔드 이력서",
        name="홍길동",
        created_at=datetime(2026, 7, 6, tzinfo=UTC),
    )

    monkeypatch.setattr(analyze, "st", fake_st)
    monkeypatch.setattr(analyze, "fetch_resumes", lambda: [resume])
    monkeypatch.setattr(
        analyze,
        "render_analysis_result",
        lambda resume_id, job_posting_id: rendered_results.append((resume_id, job_posting_id)),
    )

    analyze.render_analyze_page()

    assert fake_st.button_slot.calls[0] == {
        "label": "분석 중...",
        "type": "primary",
        "disabled": True,
    }
    assert rendered_results == [(11, 22)]
