# Agent Notes

> 구조/파일/규칙을 바꾸면 이 파일과 `.claude/CLAUDE.md`를 **항상 함께 갱신**한다(둘이 어긋나지 않게). 상세 기준은 `.claude/CLAUDE.md`.

## 디렉터리 · 파일 구조 컨벤션 (실제 구현 기준)

레이어드 구조. 책임별 디렉터리:

```
app/
├─ config/        # 설정(settings.py) · DI 컨테이너(containers.py)
├─ controllers/   # FastAPI 라우터 — 얇게: 입력 검증·HTTP 변환만
├─ services/      # 핵심 비즈니스 로직 · 오케스트레이션(DocumentService.process)
├─ repositories/  # DB 영속화
├─ crawlers/      # 채용공고 크롤러(도메인별 파일: saramin.py, wanted.py / 공통: job_postings.py, utils.py)
├─ ai/            # LLM 연동(classification/document, extraction, vision)
├─ tasks/         # Celery 태스크 — 진입점 + DI/세션 배선만
├─ cache/ · database/ · schemas/ · models/ · security/
├─ utils.py       # 범용 순수 유틸(clean_text 등)
└─ tests/
```

- 계층 책임: 컨트롤러는 얇게, 핵심 로직은 services, tasks는 진입점+배선만, repositories는 DB만. **컨트롤러는 레포지토리를 직접 호출하지 않고 서비스를 주입해 서비스가 레포지토리를 다룬다**(예: `get_parse_status` → `DocumentService.get_parse_status`, 컨트롤러는 `None`이면 404로만 매핑).
- 예외: 도메인 예외는 `app/services/errors.py`에 모아 정의하고(`UnsupportedDocumentFormatError`·`FileTooLargeError`·`DocumentFileParseError`·`InsufficientJobContentError`) 서비스에서 던진다. `HTTPException`은 만들지 않는다. import는 `from app.services.errors import ...`(`app.services.document` 재노출에 의존 금지). HTTP 매핑은 `app/main.py` 전역 핸들러(`_DOMAIN_EXCEPTION_STATUS`)에 모은다(새 예외는 여기 등록). 컨트롤러는 입력 검증·404에만 `HTTPException` 사용.
- 실패 처리·로깅: **조용한 fail-soft 금지** — `except` 폴백(기본값·`None`·빈 결과·`pass`)은 반드시 원인 로깅(외부 서비스/AI/임베딩 실패는 `warning`+, 기대 가능한 단건 스킵은 info/debug). 성공 로그는 Langfuse가 담당하므로 중복 금지, **실패·폴백 로깅은 코드 책임**(Langfuse 안 닿는 임베딩 실패는 특히 필수).
- 상태코드: 코딩된(예상 가능한) 실패는 500이 아니라 도메인 예외 → 4xx/5xx로(예: 외부 의존 서비스 일시 장애 → 503; 빈 결과로 감추지 않음). 500은 *예기치 못한* 예외에만 — `app/main.py` catch-all(`handle_unexpected_error`)이 `logger.exception`(트레이스백)으로 남기고 내부 메시지 비노출 500을 반환한다. 핸들러 로깅 레벨: 5xx=`error`/`exception`, 4xx=`info`.
- DI: 의존 객체는 `Container`로 주입. 인프라는 얇은 래퍼 클래스 + `providers.Singleton(클래스)`(예: `Database`, `RedisCache`). 워커는 `worker_database`(Factory)를 쓰고 `document_service` provider로 조립하되 세션에 묶인 repo만 호출 시점에 덮어쓴다.
- 유틸/네이밍: 상태 없는 순수 함수는 클래스/ABC 말고 모듈 함수로. 공유 범용은 `app/utils.py`, 도메인 전용은 그 도메인의 `utils.py`로(중복 제거). 외부에서 import하는 함수/상수는 `_` 없이, 모듈 내부 전용만 `_`. **폴더 이름에는 `_`를 쓰지 않는다.**
- 패키지화: 모듈이 커지거나 역할이 갈리면 폴더로 쪼개고 `__init__.py`에서 재노출해 import 경로를 유지한다(예: `ai/classification/document/`, `ai/extraction/`).
- docstring: 모든 함수/메서드에 구글 스타일 한글. 직접 `raise`가 있으면 `Raises:` 추가. 클래스/모듈 docstring은 생략.
- 검증: `uv run ruff check app`(120) · `uv run pyrefly check`(0 errors) · `uv run pytest`. 개발 전용 의존성은 `uv add --dev`.
- 도커: `docker-compose.yml`(배포 base) + `compose.local.yml`(로컬 오버레이, `-f`로 함께 지정). 시크릿은 `.env`, `.env.sample`은 값 비움.
- 모듈을 이동/분리하면 테스트 monkeypatch 대상을 "실제 사용되는 모듈"로 맞춘다(재노출만으로는 패치가 닿지 않음).
- HTTP 상태코드는 raw 숫자(예: `422`)가 아니라 `fastapi.status` 상수(예: `status.HTTP_422_UNPROCESSABLE_ENTITY`)를 쓴다. 코드·테스트 모두 동일.

## 의존성 주입(DI) 규칙

- 서비스가 사용하는 의존 객체는 `app.config.containers.Container`를 통해 주입받는다.
- 서비스 생성자나 메서드 안에서 크롤러·인프라 클래스를 직접 생성하지 않는다.
- `DocumentService`는 채용공고 크롤러를 `Container.job_posting_crawler`로 주입받는다. `DocumentService` 안에서 `JobPostingCrawler()`를 직접 호출하지 않는다.
- `JobPostingCrawler`는 도메인 크롤러 목록을 컨테이너로부터 주입받는다. 내부에서 `WantedJobPostingCrawler()`처럼 기본값으로 직접 생성하지 않는다.
- 채용공고 도메인 크롤러는 `JobPostingProtocol`을 구현한다. 새 구현체는 컨테이너에 등록하고, 도메인별 크롤링 로직을 다시 `DocumentService`에 넣지 않는다.
- Celery 워커처럼 서비스를 수동으로 구성하는 경로에서도 크롤러 의존성을 컨테이너 provider로부터 주입받아 사용한다.
- 파싱 후 문서 종류 판별은 `Container.document_classifier` / `LangChainDocumentClassifier`를 통해서만 한다. 태스크나 문서 서비스에서 LangChain을 직접 호출하지 않는다.
- 워커 처리 순서는 `문서 파싱 → 기대 문서 종류 판별 → mark_done/프로필 저장`이다. 판별 결과가 `is_expected=false`면 `mark_failed()`를 호출하고 중단한다.
- FastAPI/DI 통합 테스트는 `with app.container.<provider>.override(fake): ...`로 provider를 교체한 뒤 엔드포인트나 컨테이너가 생성한 객체를 호출한다. 가짜 객체를 인자로 직접 넘기는 방식은 DI를 의도적으로 우회하는 좁은 단위 테스트에서만 쓴다.
