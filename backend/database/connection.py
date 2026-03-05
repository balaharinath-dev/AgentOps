"""
Database connection management for AgentOps.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

# Database configuration
# Get absolute path to database file
_default_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentops.db")
DB_PATH = os.getenv("AGENTOPS_DB_PATH", _default_db_path)

# Ensure path is absolute
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.abspath(DB_PATH)

DB_URL = f"sqlite:///{DB_PATH}"

# Create engine
# For SQLite, we use StaticPool to avoid threading issues
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_connection():
    """
    Get database engine connection.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    return engine


def get_session() -> Session:
    """
    Get database session.
    
    Usage:
        with get_session() as session:
            # Use session
            session.query(WorkflowRun).all()
    
    Returns:
        Session: SQLAlchemy session instance
    """
    session = SessionLocal()
    try:
        return session
    except Exception as e:
        session.close()
        raise e


def get_db_path() -> str:
    """
    Get the database file path.
    
    Returns:
        str: Path to the SQLite database file
    """
    return DB_PATH


def get_db_url() -> str:
    """
    Get the database URL.
    
    Returns:
        str: SQLAlchemy database URL
    """
    return DB_URL
