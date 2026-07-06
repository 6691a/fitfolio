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
