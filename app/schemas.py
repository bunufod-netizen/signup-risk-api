from typing import Literal

from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254, examples=["john@example.com"])


class BulkCheckRequest(BaseModel):
    emails: list[str] = Field(min_length=1, examples=[["john@example.com", "test@mailinator.com"]])


class CheckResponse(BaseModel):
    email: str
    valid_format: bool
    domain: str | None
    domain_exists: bool | None
    mx_exists: bool | None
    disposable: bool
    role_account: bool
    free_provider: bool
    typo_suggestion: str | None
    risk: Literal["low", "medium", "high"]
    risk_score: int = Field(ge=0, le=100)
    reasons: list[str]
