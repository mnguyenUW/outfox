"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine
from app.routers import providers, ask
from sqlalchemy import text

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting up Healthcare Cost Navigator API...")
    
    # Verify database connection
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM providers"))
            count = result.scalar()
            print(f"✅ Database connected. Providers: {count}")
    except Exception as e:
        print(f"⚠️  Database connection issue: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.debug,
    description="API for searching healthcare providers and costs",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    providers.router,
    prefix="/providers",
    tags=["Providers"]
)
app.include_router(
    ask.router,
    prefix="/ask",
    tags=["AI Assistant"]
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "endpoints": {
            "providers": "/providers",
            "ai_assistant": "/ask",
            "documentation": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy",
        "database": db_status
    }