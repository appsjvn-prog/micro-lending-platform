import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.bank_account import BankAccount
from app.models.loan_product import LoanProduct

# Create a test database (SQLite in memory for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the database dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Tell FastAPI to use test database instead of real one
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    """
    Create a test client for making API requests
    This runs before each test
    """
    # Create all tables in test database
    Base.metadata.create_all(bind=engine)
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client  # This is what tests will receive
    
    # Clean up after test - drop all tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def admin_key():
    """
    Return the admin key for testing admin-only endpoints
    """
    return "adminkey"  # Use your actual admin key