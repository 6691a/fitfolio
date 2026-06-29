from typing import Any

from dependency_injector.wiring import Provide
from langchain_core.runnables import RunnableConfig


def langfuse_config(handler: Any, *, run_name: str, metadata: dict) -> RunnableConfig | None:
    """주입된 Langfuse 핸들러로 LangChain ainvoke용 config를 만든다.

    wire되지 않은 Provide marker(또는 None)면 None을 반환해 콜백을 붙이지 않는다.

    Args:
        handler: 컨테이너가 주입한 Langfuse callback handler(또는 Provide marker).
        run_name: Langfuse run 이름.
        metadata: Langfuse run 메타데이터.

    Returns:
        callbacks/run_name/metadata가 담긴 RunnableConfig, 핸들러가 없으면 None.
    """
    # Provide는 런타임에선 클래스라 isinstance가 동작하지만 pyrefly 스텁은 값으로 본다 → 그 한 줄만 무시.
    if handler is None or isinstance(handler, Provide):  # pyrefly: ignore[invalid-argument]
        return None
    return {"callbacks": [handler], "run_name": run_name, "metadata": metadata}
