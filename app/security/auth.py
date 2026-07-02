from pwdlib import PasswordHash

_PASSWORD_HASH = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """평문 비밀번호를 안전한 해시 문자열로 변환한다.

    Args:
        password: 사용자가 입력한 평문 비밀번호.

    Returns:
        저장 가능한 비밀번호 해시.
    """
    return _PASSWORD_HASH.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """평문 비밀번호가 저장된 해시와 일치하는지 검증한다.

    Args:
        password: 사용자가 입력한 평문 비밀번호.
        hashed_password: DB에 저장된 비밀번호 해시.

    Returns:
        비밀번호가 일치하면 True, 아니면 False.
    """
    return _PASSWORD_HASH.verify(password, hashed_password)
