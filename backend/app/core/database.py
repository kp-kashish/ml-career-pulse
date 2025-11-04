"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logging import log

# Create database engine with SQLite fallback
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False
    )
    log.info("Using SQLite database for development")
else:
    # PostgreSQL settings
    engine = create_engine(DATABASE_URL, echo=False)
    log.info("Using PostgreSQL database")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """
    Initialize database tables
    """
    try:
        # Import all models to register them with Base
        from app.models import models
        
        Base.metadata.create_all(bind=engine)
        log.info("Database tables created successfully")
        
        # Log created tables
        for table in Base.metadata.sorted_tables:
            log.info(f"  - Table created: {table.name}")
            
    except Exception as e:
        log.error(f"Error creating database tables: {e}")
        raise