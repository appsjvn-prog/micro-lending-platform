from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now

class EmploymentType(str, enum.Enum):
    SALARIED = "SALARIED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    BUSINESS = "BUSINESS"
    STUDENT = "STUDENT"
    UNEMPLOYED = "UNEMPLOYED"

class BorrowerProfile(Base):
    __tablename__ = "borrower_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Employment Info (required for loan eligibility)
    employment_type = Column(Enum(EmploymentType), nullable=False)
    monthly_income = Column(Float, nullable=False)
    employer_name = Column(String(100), nullable=True)
    
    # Work Experience
    current_job_tenure_months = Column(Integer, nullable=True)  # Months in current job
    total_work_experience_years = Column(Integer, nullable=True)
    
    # Loan Preferences (what borrower is looking for)
    preferred_min_amount = Column(Float, nullable=True)
    preferred_max_amount = Column(Float, nullable=True)
    preferred_tenure_months = Column(Integer, nullable=True)
    preferred_max_interest_rate = Column(Float, nullable=True)
    
    # Financial Health (will be updated by system)
    credit_score = Column(Integer, nullable=True)  # 300-900
    existing_loan_count = Column(Integer, default=0)
    total_existing_liabilities = Column(Float, default=0)
    
    # Status
    is_profile_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = relationship("User", back_populates="borrower_profile")
    # loan_applications = relationship("LoanApplication", back_populates="borrower")