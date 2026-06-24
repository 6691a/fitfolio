from pydantic import BaseModel

from app.schemas.documents import DocumentInput


class UserInputState(BaseModel):
    input: DocumentInput
