"""Location service for geographic operations."""
from typing import Optional, Tuple, List
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ZipCode, Provider


class LocationService:
    """Service for handling location-based operations."""
    
    @staticmethod
    async def get_zip_coordinates(
        db: AsyncSession,
        zip_code: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get latitude and longitude for a ZIP code.
        Returns: (latitude, longitude) or None
        """
        # Try DB first
        result = await db.execute(
            select(ZipCode).where(ZipCode.zip_code == zip_code)
        )
        zip_obj = result.scalar_one_or_none()
        if zip_obj and zip_obj.latitude and zip_obj.longitude:
            return (float(zip_obj.latitude), float(zip_obj.longitude))
        # Fallback to pgeocode for any valid US ZIP
        try:
            import pgeocode
            nomi = pgeocode.Nominatim('US')
            info = nomi.query_postal_code(zip_code)
            if info is not None and not info.empty and info.latitude and info.longitude:
                return (float(info.latitude), float(info.longitude))
        except Exception:
            pass
        return None
    
    @staticmethod
    async def find_providers_within_radius(
        db: AsyncSession,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        drg_cd: Optional[int] = None,
        drg_desc: Optional[str] = None
    ) -> List[dict]:
        """
        Find providers within a radius of a geographic point.
        Uses PostGIS for efficient spatial queries.
        """
        import logging
        logger = logging.getLogger("location_service")
        logger.warning(f"find_providers_within_radius called with: center_lat={center_lat}, center_lon={center_lon}, radius_km={radius_km}, drg_cd={drg_cd}, drg_desc={drg_desc}")

        # Build the base query with distance calculation
        query = """
            WITH provider_distances AS (
                SELECT
                    p.*,
                    pr.rating as overall_rating,
                    pr.review_count,
                    ST_Distance(
                        p.location,
                        ST_MakePoint(:lon, :lat)::geography
                    ) / 1000 AS distance_km
                FROM providers p
                LEFT JOIN provider_ratings pr ON
                    p.rndrng_prvdr_ccn = pr.provider_ccn
                    AND pr.rating_category = 'overall'
                WHERE p.location IS NOT NULL
                    AND ST_DWithin(
                        p.location,
                        ST_MakePoint(:lon, :lat)::geography,
                        :radius_meters
                    )
        """
        
        # Add DRG filtering if specified
        if drg_cd:
            query += " AND p.drg_cd = :drg_cd"
        elif drg_desc:
            # Use trigram similarity for fuzzy matching
            query += """ 
                AND (
                    p.drg_desc ILIKE :drg_pattern 
                    OR p.drg_cd::text = :drg_desc
                )
            """
        
        query += """
            )
            SELECT 
                id,
                rndrng_prvdr_ccn,
                rndrng_prvdr_org_name,
                rndrng_prvdr_city,
                rndrng_prvdr_st,
                rndrng_prvdr_state_abrvtn,
                rndrng_prvdr_zip5,
                drg_cd,
                drg_desc,
                tot_dschrgs,
                avg_submtd_cvrd_chrg,
                avg_tot_pymt_amt,
                avg_mdcr_pymt_amt,
                latitude,
                longitude,
                distance_km,
                overall_rating,
                review_count
            FROM provider_distances
            ORDER BY avg_submtd_cvrd_chrg ASC
            LIMIT 50
        """
        
        # Prepare parameters
        params = {
            'lat': center_lat,
            'lon': center_lon,
            'radius_meters': radius_km * 1000  # Convert to meters
        }
        
        if drg_cd:
            params['drg_cd'] = drg_cd
        elif drg_desc:
            params['drg_pattern'] = f'%{drg_desc}%'
            params['drg_desc'] = drg_desc
        
        # Execute query
        logger.warning(f"SQL Query: {query}")
        logger.warning(f"SQL Params: {params}")
        result = await db.execute(text(query), params)
        
        # Convert to list of dicts
        providers = []
        count = 0
        for row in result:
            providers.append({
                'id': row.id,
                'rndrng_prvdr_ccn': row.rndrng_prvdr_ccn,
                'rndrng_prvdr_org_name': row.rndrng_prvdr_org_name,
                'rndrng_prvdr_city': row.rndrng_prvdr_city,
                'rndrng_prvdr_st': row.rndrng_prvdr_st,
                'rndrng_prvdr_state_abrvtn': row.rndrng_prvdr_state_abrvtn,
                'rndrng_prvdr_zip5': row.rndrng_prvdr_zip5,
                'drg_cd': row.drg_cd,
                'drg_desc': row.drg_desc,
                'tot_dschrgs': row.tot_dschrgs,
                'avg_submtd_cvrd_chrg': float(row.avg_submtd_cvrd_chrg) if row.avg_submtd_cvrd_chrg else None,
                'avg_tot_pymt_amt': float(row.avg_tot_pymt_amt) if row.avg_tot_pymt_amt else None,
                'avg_mdcr_pymt_amt': float(row.avg_mdcr_pymt_amt) if row.avg_mdcr_pymt_amt else None,
                'latitude': float(row.latitude) if row.latitude else None,
                'longitude': float(row.longitude) if row.longitude else None,
                'distance_km': round(row.distance_km, 2),
                'overall_rating': float(row.overall_rating) if row.overall_rating else None,
                'review_count': row.review_count
            })
            count += 1
        logger.warning(f"Providers found: {count}")
        return providers