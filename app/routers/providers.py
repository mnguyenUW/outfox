"""Providers router."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db

router = APIRouter()


@router.get("")
async def search_providers(
    drg: Optional[str] = Query(None, description="DRG code or description"),
    zip: Optional[str] = Query(None, description="ZIP code", regex="^\d{5}$"),
    radius_km: Optional[float] = Query(50.0, description="Search radius in kilometers"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for healthcare providers.
    
    - **drg**: DRG code (e.g., '470') or description keyword (e.g., 'knee')
    - **zip**: 5-digit ZIP code
    - **radius_km**: Search radius in kilometers
    
    Returns list of providers sorted by average covered charges.
    """
    # TODO: Implement provider search logic
    return {
        "message": "Provider search endpoint",
        "params": {
            "drg": drg,
            "zip": zip,
            "radius_km": radius_km
        }
    }