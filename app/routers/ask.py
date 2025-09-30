"""AI Assistant router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


class AskRequest(BaseModel):
    """Request model for ask endpoint."""
    question: str


class AskResponse(BaseModel):
    """Response model for ask endpoint."""
    answer: str
    sql_query: Optional[str] = None
    confidence: float


@router.post("", response_model=AskResponse)
async def ask_assistant(
    request: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language interface for healthcare queries.
    
    Ask questions like:
    - "What's the cheapest hospital for knee replacement near 10001?"
    - "Which hospitals have the best ratings for heart surgery?"
    """
    # TODO: Implement AI assistant logic
    return AskResponse(
        answer="AI assistant endpoint is under construction",
        confidence=0.0
    )