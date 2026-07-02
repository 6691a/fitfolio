set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

dev service="":
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d {{service}}

dev-build service="":
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build {{service}}

down:
    docker compose down

down-v:
    docker compose down -v

migrate:
    docker compose exec api uv run alembic upgrade head

makemigrations message:
    docker compose exec api uv run alembic revision --autogenerate -m "{{message}}"

front:
    uv run python -m streamlit run streamlit_app/main.py

langfuse-up:
    docker compose --env-file .env.langfuse -f docker-compose.langfuse.yml up -d

langfuse-down:
    docker compose --env-file .env.langfuse -f docker-compose.langfuse.yml down

langfuse-down-v:
    docker compose --env-file .env.langfuse -f docker-compose.langfuse.yml down -v

langfuse-logs:
    docker compose --env-file .env.langfuse -f docker-compose.langfuse.yml logs -f langfuse-web langfuse-worker
