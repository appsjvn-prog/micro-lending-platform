
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional
from app.models.loan_offer import LoanOfferStatus

# Base Schema
class LoanOfferBase(BaseModel):
    offer_name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    min_amount: Decimal = Field(..., gt=0)
    max_amount: Decimal = Field(..., gt=0)
    min_tenure_months: int = Field(..., gt=0)
    max_tenure_months: int = Field(..., gt=0)
    interest_rate: Decimal = Field(..., gt=0, le=100)
    preferred_credit_score: Optional[int] = Field(None, ge=300, le=900)
    preferred_employment_types: Optional[str] = None

    @field_validator('max_amount')
    def validate_amount_range(cls, v, info):
        if info.data.get('min_amount') and v < info.data['min_amount']:
            raise ValueError('Max amount must be greater than min amount')
        return v

    @field_validator('max_tenure_months')
    def validate_tenure_range(cls, v, info):
        if info.data.get('min_tenure_months') and v < info.data['min_tenure_months']:
            raise ValueError('Max tenure must be greater than min tenure')
        return v

# Create Schema
class LoanOfferCreate(LoanOfferBase):
    loan_product_id: UUID

# Update Schema
class LoanOfferUpdate(BaseModel):
    offer_name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    min_amount: Optional[Decimal] = Field(None, gt=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    min_tenure_months: Optional[int] = Field(None, gt=0)
    max_tenure_months: Optional[int] = Field(None, gt=0)
    interest_rate: Optional[Decimal] = Field(None, gt=0, le=100)
    preferred_credit_score: Optional[int] = Field(None, ge=300, le=900)
    preferred_employment_types: Optional[str] = None
    status: Optional[LoanOfferStatus] = None

class LoanOfferMinimalResponse(BaseModel):
    id: UUID
    offer_name: str
    status: LoanOfferStatus
    created_at: datetime
    message: str = "Loan offer created successfully"

    class Config:
        from_attributes = True

# Full Response Schema
class LoanOfferResponse(LoanOfferBase):
    id: UUID
    lender_id: UUID
    loan_product_id: Optional[UUID] = None
    status: LoanOfferStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# List Response (simplified for browsing)
class LoanOfferListResponse(BaseModel):
    id: UUID
    offer_name: str
    lender_id: UUID
    min_amount: Decimal
    max_amount: Decimal
    min_tenure_months: int
    max_tenure_months: int
    interest_rate: Decimal
    status: LoanOfferStatus
    expires_at: datetime

    class Config:
        from_attributes = True