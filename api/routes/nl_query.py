"""Natural language query endpoint — reuses CLI's intent detection and routing."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cli import detect_intent, handle_query, resolve_district

router = APIRouter()


class QueryRequest(BaseModel):
    text: str = Field(..., description="Natural language query", min_length=1, max_length=500)
    lang: str = Field(default="en", description="Language code", pattern="^(en|hi|ta)$")


class QueryResponse(BaseModel):
    query: str
    intent: str
    district: str | None
    answer: str
    lang: str


@router.post("/query")
def natural_language_query(req: QueryRequest) -> QueryResponse:
    """Process a natural language query about government schemes.

    Examples:
        {"text": "misappropriation in villupuram"}
        {"text": "worst roads bihar"}
        {"text": "funds cuddalore", "lang": "en"}
    """
    intent = detect_intent(req.text)
    district = resolve_district(req.text)
    answer = handle_query(req.text)

    return QueryResponse(
        query=req.text,
        intent=intent,
        district=district,
        answer=answer,
        lang=req.lang,
    )
