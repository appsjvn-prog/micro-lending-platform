from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.lender_profile import RiskAppetite, LenderStatus

# Base Schema
class LenderProfileBase(BaseModel):
    """Base schema for lender profile"""
    profile_name: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=50)
    available_balance: float = Field(0.0, ge=0)
    total_lent: float = Field(0.0, ge=0)
    default_min_amount: Optional[float] = Field(None, gt=0)
    default_max_amount: Optional[float] = Field(None, gt=0)
    default_min_tenure: Optional[int] = Field(None, gt=0)
    default_max_tenure: Optional[int] = Field(None, gt=0)
    default_interest_rate: Optional[float] = Field(None, gt=0, le=100)
    risk_appetite: RiskAppetite = RiskAppetite.MEDIUM

    @field_validator('default_max_amount')
    def validate_amount_range(cls, v, info):
        if v and info.data.get('default_min_amount'):
            if v < info.data['default_min_amount']:
                raise ValueError('Max amount must be greater than min amount')
        return v

    @field_validator('default_max_tenure')
    def validate_tenure_range(cls, v, info):
        if v and info.data.get('default_min_tenure'):
            if v < info.data['default_min_tenure']:
                raise ValueError('Max tenure must be greater than min tenure')
        return v

# Create Schema
class LenderProfileCreate(LenderProfileBase):
    """Schema for creating lender profile"""
    pass

# Update Schema
class LenderProfileUpdate(BaseModel):
    """Schema for updating lender profile (all fields optional)"""
    profile_name: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=50)
    default_min_amount: Optional[float] = Field(None, gt=0)
    default_max_amount: Optional[float] = Field(None, gt=0)
    default_min_tenure: Optional[int] = Field(None, gt=0)
    default_max_tenure: Optional[int] = Field(None, gt=0)
    default_interest_rate: Optional[float] = Field(None, gt=0, le=100)
    risk_appetite: Optional[RiskAppetite] = None

# Response Schema
class LenderProfileResponse(LenderProfileBase):
    """Schema for lender profile response"""
    id: UUID
    user_id: UUID
    status: LenderStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Balance Update Schema (for adding funds)
class LenderBalanceUpdate(BaseModel):
    """Schema for updating lender balance"""
    amount: float = Field(..., gt=0, description="Amount to add to available balance")
    
    @field_validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

# Lender Stats Schema
class LenderStatsResponse(BaseModel):
    """Schema for lender statistics"""
    total_lent: float
    available_balance: float
    active_offers_count: int
    pending_applications_count: int
    total_interest_earned: float  # Will be calculated from transactions

    class Config:
        from_attributes = True

class LenderProfileMinimalResponse(BaseModel):
    id: UUID
    user_id: UUID
    profile_name: str
    status: str
    is_verified: bool
    created_at: datetime
    message: str = "Lender profile created successfully"

    class Config:
        from_attributes = True