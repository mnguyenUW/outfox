print("[DEBUG] app/etl/etl.py loaded")
#!/usr/bin/env python
"""ETL script to load healthcare provider data from CSV."""
import asyncio
import sys
import pandas as pd
import numpy as np
import pgeocode
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import random
from typing import Dict, List, Optional, Tuple
from sqlalchemy import text, select
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal, engine
from app.models import Provider, ZipCode, ProviderRating


class HealthcareETL:
    """ETL pipeline for healthcare provider data."""
    
    def __init__(self, csv_path: str):
        """Initialize ETL with CSV path."""
        self.csv_path = csv_path
        self.df = None
        self.zip_cache = {}
        self.nomi = pgeocode.Nominatim('us')  # US ZIP code geocoder
        self.stats = {
            'providers_loaded': 0,
            'zip_codes_loaded': 0,
            'ratings_created': 0,
            'zip_codes_geocoded': 0,
            'errors': []
        }
    
    async def run(self):
        """Run the complete ETL pipeline."""
        print("🚀 Starting Healthcare ETL Pipeline...")
        print(f"   CSV file: {self.csv_path}")
        
        try:
            # Step 1: Load and validate CSV
            self.load_csv()
            
            # Step 2: Load ZIP code geocoding data using pgeocode
            await self.load_zip_codes_with_geocoding()
            
            # Step 3: Load provider data
            await self.load_providers()
            
            # Step 4: Generate ratings for each provider
            await self.generate_provider_ratings()
            
            # Step 5: Update geographic data
            await self.update_geographic_data()
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"❌ ETL failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def load_csv(self):
        """Load and clean CSV data."""
        print("\n📁 Loading CSV data...")
        
        # Read CSV
        self.df = pd.read_csv(self.csv_path)
        print(f"   Loaded {len(self.df)} records")
        
        # Clean column names (lowercase and replace spaces)
        self.df.columns = [col.lower().replace(' ', '_') for col in self.df.columns]
        
        # Handle missing values
        self.df = self.df.fillna({
            'rndrng_prvdr_st': '',
            'rndrng_prvdr_ruca_desc': '',
            'drg_desc': ''
        })
        
        # Convert ZIP to string and pad with zeros
        self.df['rndrng_prvdr_zip5'] = self.df['rndrng_prvdr_zip5'].astype(str).str.zfill(5)
        
        # Convert CCN to string
        self.df['rndrng_prvdr_ccn'] = self.df['rndrng_prvdr_ccn'].astype(str)
        
        # Remove dollar signs and commas from financial columns if present
        financial_cols = ['avg_submtd_cvrd_chrg', 'avg_tot_pymt_amt', 'avg_mdcr_pymt_amt']
        for col in financial_cols:
            if col in self.df.columns:
                if self.df[col].dtype == 'object':
                    self.df[col] = self.df[col].str.replace('$', '').str.replace(',', '')
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Check for duplicates
        duplicates = self.df[['rndrng_prvdr_ccn', 'drg_cd']].duplicated()
        if duplicates.any():
            print(f"   ⚠️  Found {duplicates.sum()} duplicate provider-DRG combinations, keeping first")
            self.df = self.df[~duplicates]
        
        print(f"   ✅ CSV loaded and cleaned: {len(self.df)} unique records")
    
    def geocode_zip(self, zip_code: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        """
        Geocode a ZIP code using pgeocode.
        Returns: (latitude, longitude, city, state)
        """
        try:
            # Query pgeocode for ZIP information
            result = self.nomi.query_postal_code(zip_code)
            
            if pd.notna(result.latitude) and pd.notna(result.longitude):
                # Get city and state from the result
                city = result.place_name if pd.notna(result.place_name) else None
                state = result.state_code if pd.notna(result.state_code) else None
                
                return (
                    float(result.latitude),
                    float(result.longitude),
                    city,
                    state
                )
            else:
                return None, None, None, None
                
        except Exception as e:
            print(f"   ⚠️  Error geocoding ZIP {zip_code}: {e}")
            return None, None, None, None
    
    async def load_zip_codes_with_geocoding(self):
        """Load ZIP code data with real geocoding using pgeocode."""
        print("\n📍 Loading ZIP code data with geocoding...")
        
        # Get unique ZIP codes from providers
        unique_zips = self.df['rndrng_prvdr_zip5'].unique()
        print(f"   Found {len(unique_zips)} unique ZIP codes")
        print("   Geocoding ZIP codes (this may take a moment)...")
        
        async with AsyncSessionLocal() as session:
            # Check which ZIPs already exist
            existing_result = await session.execute(
                select(ZipCode.zip_code)
            )
            existing_zips = {row[0] for row in existing_result}
            
            zip_data = []
            geocoded_count = 0
            failed_zips = []
            
            for i, zip_code in enumerate(unique_zips):
                if zip_code in existing_zips:
                    # Load from database to cache
                    result = await session.execute(
                        select(ZipCode).where(ZipCode.zip_code == zip_code)
                    )
                    zip_obj = result.scalar_one()
                    if zip_obj.latitude and zip_obj.longitude:
                        self.zip_cache[zip_code] = (float(zip_obj.latitude), float(zip_obj.longitude))
                    continue
                
                # Geocode the ZIP code
                lat, lon, city_geo, state_geo = self.geocode_zip(zip_code)
                
                if lat and lon:
                    # Get city and state from provider data as fallback
                    provider_data = self.df[self.df['rndrng_prvdr_zip5'] == zip_code].iloc[0]
                    city = city_geo or provider_data['rndrng_prvdr_city']
                    state = state_geo or provider_data['rndrng_prvdr_state_abrvtn']
                    
                    zip_obj = ZipCode(
                        zip_code=zip_code,
                        city=city,
                        state_code=state,
                        latitude=Decimal(str(round(lat, 6))),
                        longitude=Decimal(str(round(lon, 6)))
                    )
                    
                    session.add(zip_obj)
                    self.zip_cache[zip_code] = (lat, lon)
                    zip_data.append(zip_obj)
                    geocoded_count += 1
                else:
                    # Fallback: use state center coordinates
                    provider_data = self.df[self.df['rndrng_prvdr_zip5'] == zip_code].iloc[0]
                    city = provider_data['rndrng_prvdr_city']
                    state = provider_data['rndrng_prvdr_state_abrvtn']
                    
                    # State center coordinates (fallback)
                    state_centers = {
                        'TX': (31.9686, -99.9018), 'CA': (36.7783, -119.4179),
                        'NY': (43.2994, -74.2179), 'FL': (27.6648, -81.5158),
                        'IL': (40.6331, -89.3985), 'PA': (41.2033, -77.1945),
                        'OH': (40.4173, -82.9071), 'MI': (44.3148, -85.6024),
                        'GA': (32.1656, -82.9001), 'NC': (35.7596, -79.0193),
                        'VA': (37.4316, -78.6569), 'WA': (47.7511, -120.7401),
                        'MA': (42.4072, -71.3824), 'AZ': (34.0489, -111.0937),
                        'TN': (35.5175, -86.5804)
                    }
                    
                    lat, lon = state_centers.get(state, (39.8283, -98.5795))  # US center as default
                    
                    zip_obj = ZipCode(
                        zip_code=zip_code,
                        city=city,
                        state_code=state,
                        latitude=Decimal(str(round(lat, 6))),
                        longitude=Decimal(str(round(lon, 6)))
                    )
                    
                    session.add(zip_obj)
                    self.zip_cache[zip_code] = (lat, lon)
                    zip_data.append(zip_obj)
                    failed_zips.append(zip_code)
                
                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"      Processed {i + 1}/{len(unique_zips)} ZIP codes...")
            
            await session.commit()
            self.stats['zip_codes_loaded'] = len(zip_data)
            self.stats['zip_codes_geocoded'] = geocoded_count
            
            # Update geography column
            await session.execute(text("""
                UPDATE zip_codes 
                SET location = ST_MakePoint(longitude::float, latitude::float)::geography 
                WHERE location IS NULL
            """))
            await session.commit()
            
        print(f"   ✅ Loaded {len(zip_data)} new ZIP codes")
        print(f"   ✅ Successfully geocoded {geocoded_count} ZIP codes")
        if failed_zips:
            print(f"   ⚠️  Used fallback coordinates for {len(failed_zips)} ZIP codes")
    
    async def load_providers(self):
        """Load provider data from DataFrame."""
        print("\n🏥 Loading provider data...")
        
        async with AsyncSessionLocal() as session:
            batch_size = 100
            total_batches = (len(self.df) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(self.df))
                batch_df = self.df.iloc[start_idx:end_idx]
                
                providers = []
                for _, row in batch_df.iterrows():
                    # Get coordinates from ZIP cache
                    zip_code = row['rndrng_prvdr_zip5']
                    lat, lon = self.zip_cache.get(zip_code, (None, None))
                    
                    provider = Provider(
                        rndrng_prvdr_ccn=str(row['rndrng_prvdr_ccn']),
                        rndrng_prvdr_org_name=row['rndrng_prvdr_org_name'],
                        rndrng_prvdr_city=row['rndrng_prvdr_city'],
                        rndrng_prvdr_st=row['rndrng_prvdr_st'],
                        rndrng_prvdr_state_fips=int(row['rndrng_prvdr_state_fips']),
                        rndrng_prvdr_zip5=row['rndrng_prvdr_zip5'],
                        rndrng_prvdr_state_abrvtn=row['rndrng_prvdr_state_abrvtn'],
                        rndrng_prvdr_ruca=Decimal(str(row['rndrng_prvdr_ruca'])),
                        rndrng_prvdr_ruca_desc=row['rndrng_prvdr_ruca_desc'],
                        drg_cd=int(row['drg_cd']),
                        drg_desc=row['drg_desc'],
                        tot_dschrgs=int(row['tot_dschrgs']),
                        avg_submtd_cvrd_chrg=Decimal(str(round(row['avg_submtd_cvrd_chrg'], 2))),
                        avg_tot_pymt_amt=Decimal(str(round(row['avg_tot_pymt_amt'], 2))),
                        avg_mdcr_pymt_amt=Decimal(str(round(row['avg_mdcr_pymt_amt'], 2))),
                        latitude=Decimal(str(lat)) if lat else None,
                        longitude=Decimal(str(lon)) if lon else None
                    )
                    providers.append(provider)
                
                # Bulk insert
                session.add_all(providers)
                await session.commit()
                
                self.stats['providers_loaded'] += len(providers)
                print(f"   Batch {batch_num + 1}/{total_batches}: Loaded {len(providers)} providers")
            
        print(f"   ✅ Loaded {self.stats['providers_loaded']} providers")
    
    async def generate_provider_ratings(self):
        """Generate a single integer rating (1-10) for each unique provider."""
        print("\n⭐ Generating provider ratings...")

        async with AsyncSessionLocal() as session:
            # Get unique provider CCNs
            result = await session.execute(
                text("SELECT DISTINCT rndrng_prvdr_ccn FROM providers")
            )
            provider_ccns = [row[0] for row in result]

            print(f"   Generating ratings for {len(provider_ccns)} unique providers...")

            ratings_data = []

            for ccn in provider_ccns:
                # Assign a single random integer rating from 1 to 10
                rating = random.randint(1, 10)
                rating_obj = ProviderRating(
                    provider_ccn=ccn,
                    rating=Decimal(str(rating)),
                    rating_category='overall',
                    review_count=random.randint(50, 1000)
                )
                ratings_data.append(rating_obj)

            # Bulk insert ratings
            session.add_all(ratings_data)
            await session.commit()

            self.stats['ratings_created'] = len(ratings_data)

            # Show rating distribution
            rating_values = [float(r.rating) for r in ratings_data]
            avg_rating = sum(rating_values) / len(rating_values)

            print(f"   ✅ Generated {len(ratings_data)} provider ratings")
            print(f"   📊 Average rating: {avg_rating:.1f}")
            print(f"   📊 Rating distribution:")
            for score in range(1, 11):
                count = sum(1 for r in rating_values if r == score)
                bar = '█' * (count * 50 // len(rating_values)) if len(rating_values) > 0 else ''
                print(f"      {score:2d}: {bar} ({count})")
    
    async def update_geographic_data(self):
        """Update geographic location data for spatial queries."""
        print("\n🗺️  Updating geographic data...")
        
        async with AsyncSessionLocal() as session:
            # Update location column for providers
            await session.execute(text("""
                UPDATE providers 
                SET location = ST_MakePoint(longitude::float, latitude::float)::geography 
                WHERE longitude IS NOT NULL 
                AND latitude IS NOT NULL 
                AND location IS NULL
            """))
            await session.commit()
            
            # Verify spatial data
            result = await session.execute(
                text("SELECT COUNT(*) FROM providers WHERE location IS NOT NULL")
            )
            count = result.scalar()
            
        print(f"   ✅ Updated geographic data for {count} providers")
    
    def print_summary(self):
        """Print ETL summary."""
        print("\n" + "=" * 50)
        print("📊 ETL Pipeline Summary")
        print("=" * 50)
        print(f"✅ Providers loaded: {self.stats['providers_loaded']}")
        print(f"✅ ZIP codes loaded: {self.stats['zip_codes_loaded']}")
        print(f"✅ ZIP codes geocoded: {self.stats['zip_codes_geocoded']}")
        print(f"✅ Ratings generated: {self.stats['ratings_created']}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        print("\n🎉 ETL pipeline completed successfully!")


async def main():
    """Main ETL execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Healthcare ETL Pipeline')
    parser.add_argument(
        '--csv',
        default='data/med_data_sample.csv',
        help='Path to CSV file'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database before loading'
    )
    
    args = parser.parse_args()
    
    # Check if CSV exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Reset database if requested
    if args.reset:
        print("🔄 Resetting database...")
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE providers, zip_codes, provider_ratings CASCADE"))
        print("   Database reset complete")
    
    # Run ETL
    etl = HealthcareETL(str(csv_path))
    await etl.run()


if __name__ == "__main__":
    asyncio.run(main())