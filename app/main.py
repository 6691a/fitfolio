from fastapi import FastAPI

from app.config.containers import Container
from app.controllers import documents

container = Container()
container.wire(modules=[documents])

app = FastAPI(title="Fitfolio")
# pyrefly: ignore [missing-attribute]
app.container = container
app.include_router(documents.router)
