"""Quick test to ensure database is ready for ETL."""
import asyncio
from app.database import AsyncSessionLocal
from app.models import Provider, ZipCode, ProviderRating
from sqlalchemy import select, func


async def test_database():
    """Test database connectivity and schema."""
    async with AsyncSessionLocal() as session:
        # Test table counts
        provider_count = await session.scalar(select(func.count(Provider.id)))
        zip_count = await session.scalar(select(func.count(ZipCode.zip_code)))
        rating_count = await session.scalar(select(func.count(ProviderRating.id)))
        
        print(f"📊 Database Status:")
        print(f"  - Providers: {provider_count} records")
        print(f"  - ZIP Codes: {zip_count} records")
        print(f"  - Ratings: {rating_count} records")
        
        if provider_count == 0:
            print("\n⚠️  Database is empty. Ready for ETL!")
        else:
            print(f"\n✅ Database contains data")
            
            # Show sample provider
            provider = await session.scalar(select(Provider).limit(1))
            if provider:
                print(f"\nSample provider:")
                print(f"  CCN: {provider.rndrng_prvdr_ccn}")
                print(f"  Name: {provider.rndrng_prvdr_org_name}")
                print(f"  DRG: {provider.drg_cd}")


if __name__ == "__main__":
    asyncio.run(test_database())