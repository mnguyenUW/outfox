"""Provider service for business logic."""
from typing import List, Optional, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.location_service import LocationService


class ProviderService:
    """Service for provider-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.location_service = LocationService()
    
    async def search_providers(
        self,
        drg: Optional[str] = None,
        zip_code: Optional[str] = None,
        radius_km: float = 50.0
    ) -> Dict:
        """
        Search for providers based on DRG, ZIP code, and radius.
        Returns providers sorted by cost (cheapest first).
        """
        # Validate inputs
        if not zip_code:
            return {
                'error': 'ZIP code is required for geographic search',
                'providers': []
            }
        
        # Get coordinates for ZIP code
        coordinates = await self.location_service.get_zip_coordinates(self.db, zip_code)
        if not coordinates:
            return {
                'error': f'ZIP code {zip_code} not found or has no coordinates',
                'providers': []
            }
        
        lat, lon = coordinates
        
        # Parse DRG input - could be a code or description
        drg_cd = None
        drg_desc = None
        
        if drg:
            # Check if it's a numeric DRG code
            try:
                drg_cd = int(drg)
            except ValueError:
                # It's a description, use for text search
                drg_desc = drg
        
        # Find providers within radius
        providers = await self.location_service.find_providers_within_radius(
            self.db,
            center_lat=lat,
            center_lon=lon,
            radius_km=radius_km,
            drg_cd=drg_cd,
            drg_desc=drg_desc
        )
        
        return {
            'total_results': len(providers),
            'search_params': {
                'drg': drg,
                'zip_code': zip_code,
                'radius_km': radius_km,
                'center_coordinates': {
                    'latitude': lat,
                    'longitude': lon
                }
            },
            'providers': providers
        }
    
    async def get_drg_suggestions(self, query: str) -> List[Dict]:
        """
        Get DRG code suggestions based on partial text.
        Useful for autocomplete functionality.
        """
        result = await self.db.execute(text("""
            SELECT DISTINCT 
                drg_cd,
                drg_desc
            FROM providers
            WHERE 
                drg_desc ILIKE :pattern
                OR drg_cd::text LIKE :code_pattern
            ORDER BY drg_cd
            LIMIT 10
        """), {
            'pattern': f'%{query}%',
            'code_pattern': f'{query}%'
        })
        
        suggestions = []
        for row in result:
            suggestions.append({
                'drg_cd': row.drg_cd,
                'drg_desc': row.drg_desc
            })
        
        return suggestions
    
    async def get_provider_details(self, provider_ccn: str) -> Optional[Dict]:
        """Get detailed information about a specific provider."""
        result = await self.db.execute(text("""
            SELECT 
                p.*,
                AVG(pr.rating) as average_rating,
                COUNT(DISTINCT pr.rating_category) as rating_categories,
                SUM(pr.review_count) as total_reviews
            FROM providers p
            LEFT JOIN provider_ratings pr ON p.rndrng_prvdr_ccn = pr.provider_ccn
            WHERE p.rndrng_prvdr_ccn = :ccn
            GROUP BY p.id
        """), {'ccn': provider_ccn})
        
        row = result.first()
        if not row:
            return None
        
        return {
            'rndrng_prvdr_ccn': row.rndrng_prvdr_ccn,
            'rndrng_prvdr_org_name': row.rndrng_prvdr_org_name,
            'address': {
                'street': row.rndrng_prvdr_st,
                'city': row.rndrng_prvdr_city,
                'state': row.rndrng_prvdr_state_abrvtn,
                'zip': row.rndrng_prvdr_zip5
            },
            'ratings': {
                'average': float(row.average_rating) if row.average_rating else None,
                'total_reviews': row.total_reviews or 0,
                'categories_rated': row.rating_categories or 0
            }
        }