# 서비스 계층 도메인 예외. HTTP 상태 매핑은 app/main.py의 _DOMAIN_EXCEPTION_STATUS에서 한다.


class DocumentFileParseError(Exception):
    pass


class UnsupportedDocumentFormatError(Exception):
    pass


class InsufficientJobContentError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class ProfileNotReadyError(Exception):
    pass


class AnalysisNotReadyError(Exception):
    pass


class ResumeNotFoundError(Exception):
    pass


class AuthConflictError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass
