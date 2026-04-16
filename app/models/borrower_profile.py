from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now
from app.models.base import AuditMixin
from app.core.enums import CaseInsensitiveEnum

class EmploymentType(CaseInsensitiveEnum):
    SALARIED = "SALARIED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    BUSINESS = "BUSINESS"
    STUDENT = "STUDENT"
    UNEMPLOYED = "UNEMPLOYED"

class BorrowerProfile(Base, AuditMixin):
    __tablename__ = "borrower_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Employment Info (required for loan eligibility)
    employment_type = Column(Enum(EmploymentType), nullable=False)
    monthly_income = Column(Numeric(10, 2), nullable=False)
    employer_name = Column(String(100), nullable=True)
    
    # Work Experience
    current_job_tenure_months = Column(Integer, nullable=True)  # Months in current job
    total_work_experience_years = Column(Integer, nullable=True)
    
    risk_score = Column(Integer, nullable=True)  # Store latest risk score
    risk_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    last_risk_calculation = Column(DateTime, nullable=True) # When last calculated
    
    # Status
    is_profile_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="borrower_profile")
    