"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text  # Add this import
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting up Healthcare Cost Navigator API...")
    # Temporarily comment out init_db until we fix it
    # await init_db()
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI app - make sure this is named 'app'
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporarily comment out routers until we create them properly
# from app.routers import providers, ask
# app.include_router(providers.router, prefix="/providers", tags=["providers"])
# app.include_router(ask.router, prefix="/ask", tags=["ai-assistant"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}