# 서비스 계층 도메인 예외. HTTP 상태 매핑은 app/main.py의 _DOMAIN_EXCEPTION_STATUS에서 한다.


class DocumentFileParseError(Exception):
    pass


class UnsupportedDocumentFormatError(Exception):
    pass


class InsufficientJobContentError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class EmbeddingUnavailableError(Exception):
    pass
