"""Providers router."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.services.provider_service import ProviderService

router = APIRouter()


@router.get("")
async def search_providers(
    drg: Optional[str] = Query(None, description="DRG code or description keyword"),
    zip: Optional[str] = Query(None, description="5-digit ZIP code", regex="^[0-9]{5}$"),
    radius_km: float = Query(50.0, ge=1.0, le=500.0, description="Search radius in kilometers"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for healthcare providers by DRG and location.
    
    - **drg**: DRG code (e.g., '470') or description keyword (e.g., 'knee replacement')
    - **zip**: 5-digit ZIP code for center of search
    - **radius_km**: Search radius in kilometers (1-500)
    
    Returns providers sorted by average covered charges (cheapest first).
    
    Example queries:
    - `/providers?drg=470&zip=10001&radius_km=50` - Find DRG 470 near NYC
    - `/providers?drg=knee&zip=90210&radius_km=25` - Search by keyword near LA
    """
    
    if not zip:
        raise HTTPException(
            status_code=400,
            detail="ZIP code is required for provider search"
        )
    
    service = ProviderService(db)
    result = await service.search_providers(
        drg=drg,
        zip_code=zip,
        radius_km=radius_km
    )
    
    if 'error' in result and result['error']:
        raise HTTPException(
            status_code=404,
            detail=result['error']
        )
    
    return result


@router.get("/drg-suggestions")
async def get_drg_suggestions(
    q: str = Query(..., min_length=2, description="Query string for DRG suggestions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get DRG code suggestions for autocomplete.
    
    - **q**: Partial DRG code or description (minimum 2 characters)
    
    Returns up to 10 matching DRG codes with descriptions.
    """
    service = ProviderService(db)
    suggestions = await service.get_drg_suggestions(q)
    return {"suggestions": suggestions}


@router.get("/{provider_ccn}")
async def get_provider_details(
    provider_ccn: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific provider.
    
    - **provider_ccn**: Provider's CMS Certification Number
    """
    service = ProviderService(db)
    details = await service.get_provider_details(provider_ccn)
    
    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Provider with CCN {provider_ccn} not found"
        )
    
    return details