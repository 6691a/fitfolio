from streamlit_app.views import analysis


class FakeColumn:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def metric(self, *_args, **_kwargs):
        return None

    def caption(self, *_args, **_kwargs):
        return None


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state = {}
        self.buttons = []

    def subheader(self, *_args, **_kwargs):
        return None

    def metric(self, *_args, **_kwargs):
        return None

    def write(self, *_args, **_kwargs):
        return None

    def columns(self, count):
        if isinstance(count, int):
            return [FakeColumn() for _ in range(count)]
        return [FakeColumn() for _ in count]

    def markdown(self, *_args, **_kwargs):
        return None

    def caption(self, *_args, **_kwargs):
        return None

    def divider(self):
        return None

    def slider(self, *_args, **_kwargs):
        return 3.0

    def text_input(self, *_args, **_kwargs):
        return ""

    def button(self, label, **kwargs):
        self.buttons.append({"label": label, **kwargs})
        return False


def test_fit_result_includes_interview_preparation_action(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(analysis, "st", fake_st)

    analysis.render_fit_result(
        {
            "overall_score": 82,
            "summary": "전반적으로 적합합니다.",
            "skill": {"score": 80},
            "career": {"score": 85},
            "education": {"score": 75},
            "matched_skills": [],
            "missing_skills": [],
            "strengths": [],
            "gaps": [],
        },
        analysis_id=3,
    )

    assert any(button["label"] == "면접 질문 준비하기" for button in fake_st.buttons)
