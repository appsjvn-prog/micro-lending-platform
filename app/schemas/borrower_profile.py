from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.borrower_profile import EmploymentType
from app.schemas.user import UserResponse

# Base Schema
class BorrowerProfileBase(BaseModel):
    employment_type: EmploymentType
    monthly_income: float = Field(0, ge=0)
    employer_name: Optional[str] = None
    current_job_tenure_months: Optional[int] = Field(None, ge=0)
    total_work_experience_years: Optional[int] = Field(None, ge=0)
    
@field_validator('monthly_income')
@classmethod
def validate_income_based_on_employment(cls, v: Decimal, info) -> Decimal:
    employment_type = info.data.get('employment_type')
        
        # Employment type to income requirement mapping
    if employment_type in [EmploymentType.STUDENT, EmploymentType.UNEMPLOYED]:
        if v < 0:
            raise ValueError('Income cannot be negative')
        return v
        
        # For others, income must be > 0
    if v <= 0:
        raise ValueError(f'Monthly income must be greater than 0 for {employment_type.value}')
        
    return v

# Create Schema
class BorrowerProfileCreate(BorrowerProfileBase):
    pass

# Update Schema
class BorrowerProfileUpdate(BaseModel):
    employment_type: Optional[EmploymentType] = None
    monthly_income: Optional[float] = Field(None, gt=0)
    employer_name: Optional[str] = None
    current_job_tenure_months: Optional[int] = Field(None, ge=0)
    total_work_experience_years: Optional[int] = Field(None, ge=0)
    
# Response Schema
class BorrowerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    employment_type: EmploymentType
    monthly_income: float
    employer_name: Optional[str] = None
    credit_score: Optional[int] = None
    existing_loan_count: Optional[int] = None
    total_existing_liabilities: Optional[float] = None
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_breakdown: Optional[dict] = None

    class Config:
        from_attributes = True

class BorrowerProfileMinimalResponse(BaseModel):
    id: UUID
    user_id: UUID
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LenderBorrowerViewResponse(BaseModel):
    """Lender's limited view of borrower profile (no sensitive data)"""
    id: UUID
    employment_type: EmploymentType
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    is_profile_complete: bool

    class Config:
        from_attributes = True