from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.borrower_profile import EmploymentType
from app.schemas.user import UserResponse

# Base Schema
class BorrowerProfileBase(BaseModel):
    employment_type: EmploymentType
    monthly_income: float = Field(..., gt=0)
    employer_name: Optional[str] = None
    current_job_tenure_months: Optional[int] = Field(None, ge=0)
    total_work_experience_years: Optional[int] = Field(None, ge=0)
    preferred_min_amount: Optional[float] = Field(None, gt=0)
    preferred_max_amount: Optional[float] = Field(None, gt=0)
    preferred_tenure_months: Optional[int] = Field(None, ge=1)
    preferred_max_interest_rate: Optional[float] = Field(None, gt=0)

    @field_validator('preferred_max_amount')
    def validate_amount_range(cls, v, info):
        if v and info.data.get('preferred_min_amount') and v < info.data['preferred_min_amount']:
            raise ValueError('Max amount must be greater than min amount')
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
    preferred_min_amount: Optional[float] = Field(None, gt=0)
    preferred_max_amount: Optional[float] = Field(None, gt=0)
    preferred_tenure_months: Optional[int] = Field(None, ge=1)
    preferred_max_interest_rate: Optional[float] = Field(None, gt=0)

# Response Schema
class BorrowerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    employment_type: EmploymentType
    monthly_income: float
    employer_name: Optional[str] = None
    credit_score: Optional[int] = None
    existing_loan_count: int
    total_existing_liabilities: float
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class BorrowerProfileMinimalResponse(BaseModel):
    id: UUID
    user_id: UUID
    employment_type: EmploymentType
    monthly_income: float
    employer_name: Optional[str] = None
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True