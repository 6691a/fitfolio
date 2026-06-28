import re


def clean_text(text: str) -> str:
    """연속 공백을 하나로 줄이고 앞뒤 공백을 제거한다.

    Args:
        text: 정리할 텍스트.

    Returns:
        공백이 정리된 텍스트.
    """
    return re.sub(r"\s+", " ", text).strip()
