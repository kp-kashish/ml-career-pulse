"""
FastAPI main application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import log
from app.core.database import init_database
from app.api import test
from app.api import test, trends, collect


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    log.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    log.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database
    init_database()
    
    yield
    
    # Shutdown
    log.info("Application shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time ML skills and trends tracker",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(test.router, prefix="/api/v1/test", tags=["test"])
app.include_router(test.router, prefix="/api/v1/test", tags=["test"])
app.include_router(trends.router, prefix="/api/v1/trends", tags=["trends"])
app.include_router(collect.router, prefix="/api/v1/collect", tags=["data-collection"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Import and include API routers (we'll add this back later)
# from app.api import scrapers
# app.include_router(scrapers.router, prefix="/api/v1/scrapers", tags=["scrapers"])