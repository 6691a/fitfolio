from typing import Protocol

from app.schemas.documents import DocumentClassification, DocumentKind


class DocumentClassifierProtocol(Protocol):
    async def classify(self, text: str, expected_kind: DocumentKind) -> DocumentClassification:
        """텍스트가 기대 문서 종류와 일치하는지 분류한다.

        Args:
            text: 판별할 문서 텍스트.
            expected_kind: 기대하는 문서 종류.

        Returns:
            판별 결과를 담은 DocumentClassification.
        """
        pass
