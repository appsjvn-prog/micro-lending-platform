from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.loan_application import LoanApplicationStatus

# Base Schema
class LoanApplicationBase(BaseModel):
    loan_offer_id: UUID
    requested_amount: float = Field(..., gt=0)
    requested_tenure: int = Field(..., gt=0)
    purpose: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

# Create Schema (for borrowers applying)
class LoanApplicationCreate(LoanApplicationBase):
    pass

# Update Schema (for lenders reviewing)
class LoanApplicationReview(BaseModel):
    status: LoanApplicationStatus  # ACCEPTED or REJECTED
    lender_notes: Optional[str] = Field(None, max_length=500)

    @field_validator('status')
    def validate_status(cls, v):
        if v not in [LoanApplicationStatus.ACCEPTED, LoanApplicationStatus.REJECTED]:
            raise ValueError('Status must be ACCEPTED or REJECTED')
        return v

# Response Schema
class LoanApplicationResponse(LoanApplicationBase):
    id: UUID
    borrower_id: UUID
    status: LoanApplicationStatus
    lender_notes: Optional[str] = None
    applied_at: datetime
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# List Response (simplified for browsing)
class LoanApplicationListResponse(BaseModel):
    id: UUID
    loan_offer_id: UUID
    borrower_id: UUID
    requested_amount: float
    requested_tenure: int
    status: LoanApplicationStatus
    applied_at: datetime

    class Config:
        from_attributes = True

# Borrower's view of their applications
class BorrowerApplicationResponse(LoanApplicationListResponse):
    offer_name: Optional[str] = None
    lender_id: Optional[UUID] = None
    interest_rate: Optional[float] = None

# Lender's view of applications to their offers
class LenderApplicationResponse(LoanApplicationListResponse):
    borrower_name: Optional[str] = None
    borrower_credit_score: Optional[int] = None
    borrower_monthly_income: Optional[float] = None

# Base response with common fields
class LoanApplicationBaseResponse(BaseModel):
    id: UUID
    loan_offer_id: UUID
    requested_amount: float
    requested_tenure: int
    status: LoanApplicationStatus
    applied_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# Borrower sees their own applications
class BorrowerLoanApplicationResponse(LoanApplicationBaseResponse):
    # Just the base fields - they don't need lender info
    pass

# Lender sees applications with borrower details
class LenderLoanApplicationResponse(LoanApplicationBaseResponse):
    borrower_name: Optional[str] = None
    borrower_email: Optional[str] = None
    borrower_phone: Optional[str] = None
    borrower_credit_score: Optional[int] = None
    borrower_monthly_income: Optional[float] = None

# Admin sees everything
class AdminLoanApplicationResponse(LoanApplicationBaseResponse):
    borrower: dict
    lender: dict
    loan_offer: dict

class LoanApplicationUpdate(BaseModel):
    """Schema for updating loan application"""
    requested_amount: Optional[float] = Field(None, gt=0)
    requested_tenure: Optional[int] = Field(None, gt=0)
    interest_rate: Optional[float] = Field(None, gt=0, le=100)  # For admin only
    
    class Config:
        from_attributes = True

# Minimal response for creation (POST)
class LoanApplicationMinimalResponse(BaseModel):
    id: UUID
    loan_offer_id: UUID
    status: LoanApplicationStatus
    applied_at: datetime
    message: str = "Loan application submitted successfully"

    class Config:
        from_attributes = True