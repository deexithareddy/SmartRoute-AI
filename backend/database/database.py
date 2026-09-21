"""
Database Configuration & Session Management

SQLite for the prototype (designed so swapping to PostgreSQL later is
a configuration change, not a rewrite).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL can be overridden via DATABASE_URL environment variable (e.g. postgresql://user:pass@host/db)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartroute.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# TODO: Define SQLAlchemy ORM entities for routes, historical runs, and simulation logs
