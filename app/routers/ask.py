"""AI Assistant router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.ai_service import AIService

router = APIRouter()


class AskRequest(BaseModel):
    """Request model for ask endpoint."""
    question: str = Field(..., min_length=5, max_length=500, description="Natural language question about healthcare costs or quality")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What's the cheapest hospital for knee replacement within 25 miles of ZIP code 10001?"
            }
        }


class AskResponse(BaseModel):
    """Response model for ask endpoint."""
    answer: str = Field(..., description="Natural language answer to the question")
    sql_query: Optional[str] = Field(None, description="Generated SQL query (for transparency)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the answer")
    results_count: Optional[int] = Field(None, description="Number of results found")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The cheapest hospital for knee replacement (DRG 470) within 25 miles of ZIP 10001 is Hospital for Special Surgery in New York, NY, with an average charge of $75,000. It has a rating of 9.2/10.",
                "sql_query": "SELECT * FROM providers WHERE drg_desc ILIKE '%knee%' AND ST_DWithin(location, (SELECT location FROM zip_codes WHERE zip_code = '10001'), 40234) ORDER BY avg_submtd_cvrd_chrg LIMIT 10",
                "confidence": 0.85,
                "results_count": 5
            }
        }


@router.post("", response_model=AskResponse)
async def ask_assistant(
    request: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language interface for healthcare queries.
    
    This endpoint uses AI to understand your question and search the database for relevant information.
    
    ## Example Questions:
    
    ### Cost-related queries:
    - "What's the cheapest hospital for knee replacement near 10001?"
    - "Find affordable heart surgery options in California"
    - "Compare costs for DRG 470 within 50 miles of Chicago"
    
    ### Quality-related queries:
    - "Which hospitals have the best ratings for cardiac procedures?"
    - "Find highly-rated orthopedic hospitals in New York"
    - "What's the best rated hospital for hip replacement near 90210?"
    
    ### Combined queries:
    - "Find good but affordable hospitals for back surgery near Boston"
    - "Show me hospitals with DRG 247 that have ratings above 8"
    
    ### Geographic queries:
    - "List all hospitals offering knee surgery within 30 miles of 10001"
    - "What procedures are available in Miami?"
    
    The AI will interpret your question, generate an appropriate database query,
    and provide a natural language response with the results.
    """
    
    # Validate API key is configured
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.openai_api_key or settings.openai_api_key == "sk-placeholder":
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Please set the OPENAI_API_KEY environment variable."
        )
    
    try:
        ai_service = AIService(db)
        result = await ai_service.process_question(request.question)
        
        return AskResponse(
            answer=result["answer"],
            sql_query=result.get("sql_query"),
            confidence=result.get("confidence", 0.0),
            results_count=result.get("results_count")
        )
        
    except Exception as e:
        print(f"Error in ask endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again."
        )