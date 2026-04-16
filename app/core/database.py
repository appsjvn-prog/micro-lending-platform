from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base 
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Set up logging to see what's happening
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Create database engine with more options
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=True,  # This will show SQL queries (helpful for debugging)
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Test connection on startup
def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print(" Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

# Call test connection
test_connection()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()