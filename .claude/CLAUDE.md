# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git / 커밋 정책

- **에이전트는 절대 `git commit`을 실행하지 않는다.**
- 커밋 생성은 항상 사용자가 직접 한다.
- 변경이 완료되면 작업트리 상태와 검증 결과만 보고하고, 커밋 명령 실행이나 커밋 생성은 제안하지 않는다.
- 사용자가 명시적으로 커밋을 요청하더라도, 이 저장소의 정책상 커밋은 사용자가 직접 해야 한다고 안내한다.

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

## Project status

구현이 진행 중이며, 실제 코드는 `app/` 패키지 아래 레이어드 구조로 존재한다(FastAPI API + Celery 워커 + Streamlit 프런트). 디렉터리/파일 구조와 규칙은 아래 "디렉터리 · 파일 구조 컨벤션" 섹션이 1차 기준이다. 본 문서에는 **실제 코드와 일치하는 내용만** 둔다(아직 만들지 않은 설계·로드맵은 여기 기록하지 않는다).

## What Fitfolio is

Fitfolio는 사용자의 이력서/자기소개서/포트폴리오를 채용공고(PDF·이미지·URL·붙여넣기 텍스트)와 비교해 적합도와 개선 피드백을 주는 것을 목표로 한다. **현재 구현 범위는 문서 수집 → 파싱 → 문서 유형 분류 → 프로필 추출까지**이며, 적합도 점수·리포트·면접질문 생성은 아직 없다. v1은 사용자가 직접 올린 문서만 다룬다(채용사이트 크롤링·자동 추천·자동 지원 없음).

## Commands

- Python >=3.13, 의존성은 `uv`(`pyproject.toml` + `uv.lock`)로만 관리한다. pip/poetry/conda 워크플로를 도입하지 않는다.
- 로컬 시작 전 `.env.sample`을 기준으로 `.env`를 준비한다. 시크릿 값은 커밋하지 않는다.
- Install/sync deps: `uv sync`
- Add a dependency: `uv add <package>` (개발 전용은 `uv add --dev <package>`)
- Run all local services: `just dev`
  - 내부적으로 `docker-compose.yml` + `docker-compose.local.yml` 오버레이를 함께 올린다.
  - 주요 포트: API `http://localhost:8000`, Streamlit `http://localhost:8501`, PostgreSQL `localhost:5432`, Redis `localhost:6379`.
- Run one service: `just dev api`, `just dev worker`, `just dev front`, `just dev db`, `just dev redis`
- Rebuild while starting: `just dev-build` or `just dev-build api`
- Stop containers: `just down`
- Stop and remove volumes: `just down-v`
- Apply DB migrations: `just migrate`
- Create a migration: `just makemigrations "message"`
- Run only Streamlit as a local process: `just front`
  - API는 별도로 `localhost:8000`에서 떠 있어야 하고, `API_BASE_URL`은 `.env`를 따른다.
- LLM 트레이싱은 LangSmith를 쓴다(SaaS). `.env`의 `LANGSMITH_*` env 변수로 자동 동작하며, 켜려면 `LANGSMITH_TRACING=true`. 별도 로컬 스택은 없다.
- Lint / type / test: `uv run ruff check app` · `uv run pyrefly check` · `uv run pytest`

테스트는 `app/tests/`에 있고 pytest로 돌린다. LLM/외부 호출 테스트는 실제 모델을 부르지 말고 가짜 분류기/구조화 추출이나 `app.container.<provider>.override(...)`로 대체한다.

## 디렉터리 · 파일 구조 컨벤션 (실제 구현 기준)

> 구조/파일을 바꾸면 이 섹션과 `.codex/AGENTS.md`를 **항상 함께 갱신**한다(둘이 어긋나지 않게).

레이어드 구조이며 책임별로 디렉터리를 나눈다(controller → service → repository 계층 분리).

```
app/
├─ config/        # 설정(settings.py) · DI 컨테이너(containers.py)
├─ controllers/   # FastAPI 라우터 — 얇게: 입력 검증·HTTP 변환만
├─ services/      # 핵심 비즈니스 로직 · 오케스트레이션 (예: DocumentService.process)
├─ repositories/  # DB 영속화 (SQLAlchemy 세션)
├─ crawlers/      # 채용공고 크롤러 (도메인별 파일 분리)
├─ ai/            # LLM 연동 (문서 분류기·구조화 추출·비전)
├─ tasks/         # Celery 태스크 — 진입점 + DI/세션 배선만
├─ database/      # 엔진/세션
├─ schemas/       # Pydantic 계약(요청/응답·스테이지 간 데이터)
├─ models/        # SQLAlchemy ORM 모델
├─ security/      # URL 가드 등 보안 경계
├─ utils.py       # 범용 순수 유틸(clean_text 등)
└─ tests/         # 테스트
```

### 계층 책임
- 컨트롤러는 얇게: 입력 검증·HTTP 상태/예외 변환만. 비즈니스 로직 금지. **레포지토리를 직접 호출하지 않고 서비스를 주입해 서비스가 레포지토리를 다루게 한다**(예: `get_parse_status` → `DocumentService.get_parse_status`, 컨트롤러는 `None`이면 404로만 매핑).
- 핵심 로직은 services에 둔다. 파싱→검증→저장 같은 흐름도 서비스 메서드(`process()`)로 오케스트레이션한다.
- tasks(Celery)는 Celery 진입점 + DI/세션 배선 + 서비스 호출만. 핵심 로직을 태스크에 두지 않는다.
- repositories는 DB 접근만 담당한다.

### 예외 처리
- 도메인 예외는 `app/services/errors.py`에 모아 정의하고 서비스에서 던진다(`UnsupportedDocumentFormatError`, `FileTooLargeError`, `DocumentFileParseError`, `InsufficientJobContentError`). 서비스는 `HTTPException`을 만들지 않는다(FastAPI 결합 제거). import는 `from app.services.errors import ...`를 쓴다(`app.services.document` 재노출에 의존하지 않는다).
- HTTP 상태 매핑은 `app/main.py`의 전역 예외 핸들러(`_DOMAIN_EXCEPTION_STATUS`)에서 한 곳에 모은다. 새 도메인 예외를 추가하면 이 매핑에 상태코드를 등록한다.
- 컨트롤러는 요청 단위 입력 검증과 404(리소스 없음)에만 `HTTPException`을 쓴다.
- HTTP 상태코드는 raw 숫자(예: `422`)가 아니라 `fastapi.status` 상수(예: `status.HTTP_422_UNPROCESSABLE_ENTITY`)를 사용한다. 코드·테스트 모두 동일하게 적용한다.

#### 실패 처리 · 로깅 정책 (중요)
- **실패를 조용히 삼키지 않는다.** `except`로 폴백(기본값 반환·`None`·빈 결과·`pass`)하는 경로는 **반드시 원인을 로깅**한다. 최소 `logger.warning("...: error=%s", exc)`로 무엇이/왜 실패했는지 남긴다. fail-soft(전체를 막지 않으려 폴백)는 허용하지만, "조용한 fail-soft"는 금지다.
- 성공 경로의 결과/요청 로그는 LangSmith 트레이스가 담당하므로 중복 로깅하지 않는다. **로깅은 실패·폴백 경로의 책임**이다(예: AI 구조화 실패 후 규칙 폴백, 비전/임베딩 호출 실패, 크롤러 폴백). LangSmith가 닿지 않는 경로(임베딩 등)의 실패는 특히 반드시 로깅한다.
- 기대 가능한 단건 스킵(예: 이미지 한 장 HTTP 실패 후 `continue`)은 과도하지 않게 info/debug로 남기고, 외부 서비스(AI/임베딩/크롤링) 호출 실패처럼 진단이 필요한 실패는 warning 이상으로 남긴다.
- **사용자 응답이 있는 API는 실패를 500이 아닌 의미 있는 상태코드로 돌려준다.** 폴백으로 빈 결과를 주면 "실패"가 "결과 없음"으로 오인되는 경우(예: 외부 의존 서비스 일시 장애)에는 도메인 예외를 던져 적절한 4xx/5xx로 매핑한다(예: 외부 서비스 장애 → 503). 서비스는 `HTTPException`을 만들지 않고 도메인 예외를 던지며, 상태 매핑은 `_DOMAIN_EXCEPTION_STATUS`에 등록한다.
- **500은 코딩된(예상 가능한) 실패에 쓰지 않는다.** 우리가 인지하는 실패 조건은 전부 도메인 예외 → 4xx/5xx로 매핑하고, 500은 *예기치 못한* 예외에만 남긴다. `app/main.py`의 catch-all 핸들러(`handle_unexpected_error`)가 매핑되지 않은 예외를 `logger.exception`(트레이스백 포함)으로 남기고 일반화된 500 JSON으로 응답한다 — 내부 예외 메시지는 사용자에게 노출하지 않는다. 새로 알게 된 실패 조건은 catch-all 500에 방치하지 말고 도메인 예외로 승격한다.
- 핸들러 로깅 레벨: 5xx(서버 책임)는 `error`/`exception`으로 남겨 개발자가 즉시 인지·수정하게 하고, 4xx(클라이언트 입력)는 `info`로 남겨 노이즈를 분리한다.

- 모든 의존 객체는 `app.config.containers.Container`로 주입한다. 서비스 생성자/메서드에서 인프라·크롤러를 직접 생성하지 않는다.
- 인프라는 얇은 래퍼 클래스 + `providers.Singleton(클래스)` 방식으로 등록한다(예: `Database`, `RedisCache`). `providers.Resource`(제너레이터) 대신 클래스 방식을 쓴다.
- 워커는 이벤트 루프 문제로 `worker_database`(Factory, 태스크마다 새 인스턴스)를 사용한다. 서비스는 컨테이너의 `document_service` provider로 조립하되, 세션에 묶인 repo만 호출 시점에 덮어쓴다(`Provide[Container.document_service.provider]`).

### 크롤러 구조
- 도메인 크롤러는 각 파일로 둔다: `crawlers/saramin.py`, `crawlers/wanted.py`.
- 공통 계약(`JobPostingProtocol`, `JobPostingCrawlResult`, 예외)과 최상위 조립기 `JobPostingCrawler`는 `crawlers/job_postings.py`, 공유 순수 헬퍼는 `crawlers/utils.py`에 둔다.
- 새 도메인 추가 시 `JobPostingProtocol` 구현 → 컨테이너 등록 → 전용 테스트. 도메인별 크롤링 로직을 `DocumentService`로 되돌리지 않는다.

### 유틸 분리 / 네이밍
- 상태 없는 순수 함수는 ABC/클래스에 넣지 말고 모듈 함수로 둔다.
- 여러 곳이 공유하는 범용 유틸은 중립 위치 `app/utils.py`로, 특정 도메인 전용 유틸은 그 도메인의 `utils.py`로 분리한다(중복 제거, 단일 출처 유지).
- 모듈로 분리해 외부에서 import하는 함수/상수는 `_` 접두사를 붙이지 않는다. 모듈 내부에서만 쓰는 것만 `_`를 유지한다(예: `_image_dimensions`).
- **폴더 이름에는 가능하면 `_`를 쓰지 않는다.** 파일/모듈명도 역할 기반의 짧은 이름을 선호한다.

### 추상화 수준 (클래스 vs 함수, 과한 관습 지양)
- 클래스 + `Protocol`은 **DI로 주입하고 구현을 교체/모킹해야 할 때만** 만든다(예: `DocumentClassifierProtocol` + `LangChainDocumentClassifier` — 컨테이너 주입·테스트 override 대상).
- 상태 없는 단발 호출은 모듈 **함수**로 둔다(예: `ai/extraction`, `ai/vision`). 직접 import해서 쓰고, 테스트는 모듈 함수 monkeypatch로 대체한다.
- 과한 관습은 쓰지 않는다: 모든 서비스에 인터페이스+Impl 만들기, DTO↔ORM 매퍼 레이어 남발, getter/setter·builder·불필요한 ABC. Pydantic(`model_validate`/`model_dump`)과 dependency-injector로 충분하다.

### 모듈 → 패키지 구조화
- 모듈이 커지거나 역할(인터페이스/구현/에러)이 갈리면 폴더 패키지로 쪼갠다. 예: `ai/classification/document/`(`protocol.py`·`langchain.py`·`errors.py`).
- `__init__.py`에서 공개 심볼을 재노출해 import 경로(`from app.ai.classification.document import ...`)를 안정적으로 유지한다.
- 폴더명 `_` 금지 규칙에 따라 `document_classifier`(언더스코어) 대신 `classification/document`처럼 언더스코어 없는 계층으로 둔다.
- 현재는 레이어별(package-by-layer) 구성이다. 한 도메인이 controller/service/repo/schema에 걸쳐 커지면 기능별(package-by-feature) 묶음 전환을 검토한다.

### docstring
- 모든 함수/메서드에 구글 스타일 한글 docstring을 단다. 함수 본문에 직접 `raise`가 있으면 `Raises:` 섹션을 추가한다. 클래스/모듈 docstring은 생략한다.

### 테스트
- FastAPI/DI 통합 테스트는 `with app.container.<provider>.override(fake): ...`로 교체한다.
- 모듈을 분리/이동하면 monkeypatch 대상을 "그 이름이 실제로 사용되는 모듈"로 맞춘다(재노출만으로는 패치가 닿지 않는다).

### 도커
- `docker-compose.yml` = 배포 지향 base/prod compose(바인드 마운트·watch·reload 없음).
- `docker-compose.local.yml` = 로컬 개발 오버레이(코드 변경 시 자동 재시작·바인드 마운트). 자동 병합되지 않으므로 `just dev` 또는 `docker compose -f docker-compose.yml -f docker-compose.local.yml up`로 실행한다. 실 배포는 `docker-compose.yml`만 사용한다.

### 설정 / 시크릿
- 설정은 pydantic-settings + `.env`. `.env.sample`은 키만 남기고 값은 비운다(시크릿 커밋 금지).
