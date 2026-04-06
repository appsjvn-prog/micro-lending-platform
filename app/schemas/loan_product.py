from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.loan_product import InterestType, LoanProductStatus, RepaymentDaySource, RepaymentFrequency

# ---------- Platform Limits (only for amount and tenure) ----------
MIN_LOAN_AMOUNT = 5000
MAX_LOAN_AMOUNT = 5000000
MIN_TENURE_MONTHS = 1
MAX_TENURE_MONTHS = 60

# ---------- Base Schema ----------
class LoanProductBase(BaseModel):
    """Base schema for loan product"""
    name: str = Field(..., min_length=3, max_length=100, example="Personal Loan"    )
    min_amount: Decimal = Field(..., gt=0, ge=MIN_LOAN_AMOUNT, le=MAX_LOAN_AMOUNT, example=5000.00)
    max_amount: Decimal = Field(..., gt=0, ge=MIN_LOAN_AMOUNT, le=MAX_LOAN_AMOUNT, example=50000.00)
    min_tenure_months: int = Field(..., gt=0, ge=MIN_TENURE_MONTHS, le=MAX_TENURE_MONTHS, example=6)
    max_tenure_months: int = Field(..., gt=0, ge=MIN_TENURE_MONTHS, le=MAX_TENURE_MONTHS, example=24)
    interest_type: InterestType
    min_interest_rate: Decimal = Field(..., gt=0, example=5.0)  # No hardcoded limits
    max_interest_rate: Decimal = Field(..., gt=0, example=20.0)  # No hardcoded limits
    
    # Repayment Config
    repayment_frequency: RepaymentFrequency = RepaymentFrequency.MONTHLY
    repayment_day_source: RepaymentDaySource = RepaymentDaySource.DISBURSEMENT_DATE
    grace_period_days: int = Field(3, ge=0, le=30)
    late_fee_percentage: Decimal = Field(2.0, ge=0, le=100)
    
    @field_validator('max_amount')
    def validate_amount_range(cls, v, info):
        if 'min_amount' in info.data and v <= info.data['min_amount']:
            raise ValueError('max_amount must be greater than min_amount')
        return v
    
    @field_validator('max_tenure_months')
    def validate_tenure_range(cls, v, info):
        if 'min_tenure_months' in info.data and v <= info.data['min_tenure_months']:
            raise ValueError('max_tenure_months must be greater than min_tenure_months')
        return v
    
    @field_validator('max_interest_rate')
    def validate_interest_range(cls, v, info):
        if 'min_interest_rate' in info.data and v <= info.data['min_interest_rate']:
            raise ValueError('max_interest_rate must be greater than min_interest_rate')
        return v

# ---------- Create Schema ----------
class LoanProductCreate(LoanProductBase):
    """Schema for creating a new loan product"""
    status: LoanProductStatus = LoanProductStatus.ACTIVE

# ---------- Update Schema ----------
class LoanProductUpdate(BaseModel):
    """Schema for updating loan product - all fields optional"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, example="Personal Loan")
    min_amount: Optional[Decimal] = Field(None, gt=0, ge=MIN_LOAN_AMOUNT, le=MAX_LOAN_AMOUNT, example=5000.00)
    max_amount: Optional[Decimal] = Field(None, gt=0, ge=MIN_LOAN_AMOUNT, le=MAX_LOAN_AMOUNT, example=50000.00)
    min_tenure_months: Optional[int] = Field(None, gt=0, ge=MIN_TENURE_MONTHS, le=MAX_TENURE_MONTHS, example=6)
    max_tenure_months: Optional[int] = Field(None, gt=0, ge=MIN_TENURE_MONTHS, le=MAX_TENURE_MONTHS, example=24)
    interest_type: Optional[InterestType] = None
    min_interest_rate: Optional[Decimal] = Field(None, gt=0, example=5.0)  # ✅ No hardcoded limits
    max_interest_rate: Optional[Decimal] = Field(None, gt=0, example=20.0)  # ✅ No hardcoded limits
    status: Optional[LoanProductStatus] = None

    @field_validator('max_amount')
    def validate_amount_range(cls, v, info):
        if v is not None and 'min_amount' in info.data and info.data['min_amount'] is not None:
            if v <= info.data['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v
    
    @field_validator('max_tenure_months')
    def validate_tenure_range(cls, v, info):
        if v is not None and 'min_tenure_months' in info.data and info.data['min_tenure_months'] is not None:
            if v <= info.data['min_tenure_months']:
                raise ValueError('max_tenure_months must be greater than min_tenure_months')
        return v
    
    @field_validator('max_interest_rate')
    def validate_interest_range(cls, v, info):
        if v is not None and 'min_interest_rate' in info.data and info.data['min_interest_rate'] is not None:
            if v <= info.data['min_interest_rate']:
                raise ValueError('max_interest_rate must be greater than min_interest_rate')
        return v

# ---------- Response Schema ----------
class LoanProductResponse(LoanProductBase):
    """Complete loan product details sent back to client"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: LoanProductStatus
    created_at: datetime
    updated_at: datetime

class LoanProductMinimalResponse(BaseModel):
    """Minimal loan product info for listing - only id and name"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    status: str
    message: str = "Loan product created successfully"