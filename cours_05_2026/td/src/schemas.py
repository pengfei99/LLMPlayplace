from pydantic import BaseModel, Field


class FinalAnswer(BaseModel):
    answer: str = Field(description="Final answer to display to the user")
    sources: list[str] = Field(
        default_factory=list,
        description="List of source paths or source identifiers used for the answer",
    )
