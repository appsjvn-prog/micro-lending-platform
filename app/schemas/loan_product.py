from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.loan_product import InterestType, LoanProductStatus

# ---------- Base Schema ----------
class LoanProductBase(BaseModel):
    """Base schema for loan product"""
    name: str = Field(..., min_length=3, max_length=100)
    min_amount: Decimal = Field(..., ge=5000, le=1000000, description="Minimum loan amount")
    max_amount: Decimal = Field(..., ge=5000, le=1000000, description="Maximum loan amount")
    min_tenure_months: int = Field(..., gt=0, le=36, description="Minimum tenure in months")
    max_tenure_months: int = Field(..., gt=0, le=36, description="Maximum tenure in months")
    interest_type: InterestType
    min_interest_rate: Decimal = Field(...,gt=0,le=30,description="Minimum interest rate % (0-30%)")
    max_interest_rate: Decimal = Field(..., gt=0, le=36, description="Maximum interest rate % (0-36%, must be > min_rate)")
    
    @field_validator('max_amount')
    def validate_amount_range(cls, v, info):
        """Ensure max_amount > min_amount"""
        if 'min_amount' in info.data and v <= info.data['min_amount']:
            raise ValueError('max_amount must be greater than min_amount')
        return v
    
    @field_validator('min_amount')
    def validate_min_amount(cls, v):
        if v < 5000:
            raise ValueError('Minimum loan amount must be at least ₹5,000')
        return v
    
    @field_validator('max_tenure_months')
    def validate_tenure_range(cls, v, info):
        """Ensure max_tenure > min_tenure"""
        if 'min_tenure_months' in info.data and v <= info.data['min_tenure_months']:
            raise ValueError('max_tenure_months must be greater than min_tenure_months')
        return v
    
    @field_validator('max_interest_rate')
    def validate_interest_range(cls, v, info):
        if 'min_interest_rate' in info.data and v <= info.data['min_interest_rate']:
            raise ValueError('max_interest_rate must be greater than min_interest_rate')
        if v > 36:
            raise ValueError('max_interest_rate cannot exceed 36%')
        return v
    

    @field_validator('min_interest_rate')
    def validate_min_rate(cls, v):
        if v < 8:  # 👈 8% is realistic minimum
            raise ValueError('min_interest_rate must be at least 8%')
        if v > 30:
            raise ValueError('min_interest_rate cannot exceed 30%')
        return v

# ---------- Create Schema ----------
class LoanProductCreate(LoanProductBase):
    """Schema for creating a new loan product"""
    status: LoanProductStatus = LoanProductStatus.ACTIVE

# ---------- Update Schema ----------
class LoanProductUpdate(BaseModel):
    """Schema for updating loan product - all fields optional"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    min_amount: Optional[Decimal] = Field(None, gt=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    min_tenure_months: Optional[int] = Field(None, gt=0, le=36)
    max_tenure_months: Optional[int] = Field(None, gt=0, le=36)
    interest_type: Optional[InterestType] = None
    min_interest_rate: Optional[Decimal] = Field(None, gt=0, le=30)
    max_interest_rate: Optional[Decimal] = Field(None, gt=0, le=36)
    status: Optional[LoanProductStatus] = None

# ---------- Response Schema ----------
class LoanProductResponse(LoanProductBase):  # 👈 Inherit from Base!
    """Complete loan product details sent back to client"""
    model_config = ConfigDict(from_attributes=True)
    
    # Add server-generated fields to the inherited product fields
    id: UUID
    status: LoanProductStatus  # Override to make it required in response
    created_at: datetime
    updated_at: datetime
    
    