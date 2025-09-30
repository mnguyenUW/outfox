"""Initialize database with schema and extensions."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine, Base
from app.config import get_settings
from sqlalchemy import text


async def init_db():
    """Initialize database with extensions and schema."""
    settings = get_settings()
    import asyncio
    print(f"[init_db] event loop id: {id(asyncio.get_event_loop())}")
    print(f"[init_db] engine id: {id(engine)}")
    print(f"Initializing database at: {settings.database_url}")
    
    async with engine.begin() as conn:
        # Create extensions
        print("Creating PostgreSQL extensions...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        
        # Import all models to ensure they're registered
        from app.models import Provider, ZipCode, ProviderRating
        
        # Drop all tables for fresh start (remove in production!)
        print("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database schema created successfully!")
        
        # Verify extensions
        result = await conn.execute(text("SELECT PostGIS_version()"))
        version = result.scalar()
        print(f"✅ PostGIS version: {version}")
        
        # List created tables
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """))
        tables = [row[0] for row in result]
        print(f"✅ Created tables: {', '.join(tables)}")

    import asyncio
    print(f"[verify_schema] event loop id: {id(asyncio.get_event_loop())}")
    print(f"[verify_schema] engine id: {id(engine)}")

async def verify_schema():
    """Verify the database schema is correct."""
    async with engine.connect() as conn:
        # Check providers table columns
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'providers' 
            ORDER BY ordinal_position
        """))
        
        print("\n📋 Providers table structure:")
        for col, dtype in result:
            print(f"  - {col}: {dtype}")


if __name__ == "__main__":
    async def main():
        await init_db()
        await verify_schema()
    asyncio.run(main())