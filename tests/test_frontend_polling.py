import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit_app.settings import f_settings


def test_frontend_parse_poll_interval_defaults_to_ten_seconds() -> None:
    assert getattr(f_settings, "PARSE_POLL_INTERVAL_SECONDS", None) == 10


def test_parse_result_polling_uses_frontend_setting() -> None:
    source = Path("streamlit_app/main.py").read_text()
    tree = ast.parse(source)
    fetch_parse_result = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "fetch_parse_result"
    )

    sleep_calls = [
        node
        for node in ast.walk(fetch_parse_result)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "time"
        and node.func.attr == "sleep"
    ]

    assert len(sleep_calls) == 1
    sleep_arg = sleep_calls[0].args[0]
    assert isinstance(sleep_arg, ast.Attribute)
    assert isinstance(sleep_arg.value, ast.Name)
    assert sleep_arg.value.id == "f_settings"
    assert sleep_arg.attr == "PARSE_POLL_INTERVAL_SECONDS"
