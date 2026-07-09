from streamlit_app.views.analyze import render_analyze_page
from streamlit_app.views.auth import render_login_page, render_signup_page
from streamlit_app.views.history import (
    SELECTED_ANALYSIS_KEY,
    render_analysis_detail,
    render_analysis_history_list,
)
from streamlit_app.views.preferences import render_preferences_page
from streamlit_app.views.resumes import (
    SELECTED_RESUME_KEY,
    render_resume_detail,
    render_resume_list,
)
from streamlit_app.views.search import (
    SELECTED_JOB_KEY,
    render_job_posting_detail,
    render_job_posting_list,
)

__all__ = [
    "SELECTED_ANALYSIS_KEY",
    "SELECTED_JOB_KEY",
    "SELECTED_RESUME_KEY",
    "render_analysis_detail",
    "render_analysis_history_list",
    "render_analyze_page",
    "render_job_posting_detail",
    "render_job_posting_list",
    "render_login_page",
    "render_preferences_page",
    "render_resume_detail",
    "render_resume_list",
    "render_signup_page",
]
