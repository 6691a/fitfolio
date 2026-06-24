# from pydantic import BaseModel, Field
#
# from app.ai.inputs import UserInputState
# from app.ai.states import ParsedResumeState
#
#
# class ResumeGraphState(BaseModel):
#     user_input: UserInputState | None = None
#     parsed_resume: ParsedResumeState | None = None
#     # analysis: ResumeAnalysisResult | None = None
#     errors: list[str] = Field(default_factory=list)
