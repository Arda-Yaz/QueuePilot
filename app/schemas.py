"""Request validation and response schemas for the ticket API."""

from pydantic import BaseModel, Field, field_validator


class TicketRequest(BaseModel):
    text: str = Field(
        min_length=3,
        max_length=5000,
        examples=["I cannot access the shared network drive"],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Ticket text must contain at least 3 non-whitespace characters.")
        return value


class TopPrediction(BaseModel):
    category: str
    probability: float


class PredictionResponse(BaseModel):
    category: str
    confidence: float
    threshold: float
    needs_manual_review: bool
    top_3: list[TopPrediction]


