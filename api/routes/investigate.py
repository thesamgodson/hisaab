"""LLM-powered investigative assistant endpoint.

POST /api/v1/investigate

Users supply their own API key (BYOK). Keys are never stored, logged, or
included in any response. Only SELECT queries are executed against the DB.

NOTE: This endpoint does not implement rate limiting itself.
      Deploy a rate-limiting middleware (e.g. slowapi) in front of the API
      to prevent abuse — each request makes 2 LLM calls on the user's key.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from llm.investigator import investigate

router = APIRouter()

Provider = Literal["gemini", "openai", "groq", "together"]


class InvestigateRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language question about welfare scheme data",
        min_length=5,
        max_length=1000,
        examples=["Which districts in Bihar have the most MGNREGA misappropriation?"],
    )
    api_key: str = Field(
        ...,
        description="Your LLM provider API key — never stored",
        min_length=10,
    )
    provider: Provider = Field(
        default="gemini",
        description="LLM provider: 'gemini', 'openai', 'groq', or 'together'",
    )
    model: str | None = Field(
        default=None,
        description=(
            "Optional model name override. "
            "Defaults: gemini-2.0-flash, gpt-4o-mini, llama-3.3-70b-versatile"
        ),
    )


class SourceRef(BaseModel):
    table: str
    source_url: str


class InvestigateResponse(BaseModel):
    question: str
    sql: str
    results: list[dict[str, Any]]
    narrative: str
    sources: list[SourceRef]
    provider_used: str
    model_used: str
    truncated: bool


@router.post("/investigate", response_model=InvestigateResponse)
def run_investigation(req: InvestigateRequest) -> InvestigateResponse:
    """Run an LLM-powered investigation against the Hisaab database.

    Provide your own API key for the chosen provider (BYOK). The system will:
    1. Ask the LLM to generate SQL for your question.
    2. Validate and execute the SQL (SELECT only).
    3. Ask the LLM to narrate the findings with citations.

    The API key is used only for this request and is never stored or logged.

    Example request body::

        {
            "question": "Which districts in Bihar have the most MGNREGA misappropriation?",
            "api_key": "AIzaSy...",
            "provider": "gemini"
        }
    """
    try:
        result = investigate(
            question=req.question,
            api_key=req.api_key,
            provider=req.provider,
            model=req.model,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail=f"LLM provider package not installed: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Investigation failed: {exc}",
        ) from exc
    except Exception as exc:
        # Surface LLM API errors (auth failures, quota, etc.) as 502.
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {exc}",
        ) from exc

    return InvestigateResponse(
        question=result.question,
        sql=result.sql,
        results=result.results,
        narrative=result.narrative,
        sources=[SourceRef(**s) for s in result.sources],
        provider_used=result.provider_used,
        model_used=result.model_used,
        truncated=result.truncated,
    )
