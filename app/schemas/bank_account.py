from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.bank_account import AccountType

# Base Schema
class BankAccountBase(BaseModel):
    """Base schema for bank account"""
    bank_name: str = Field(..., min_length=2, max_length=100)
    account_holder_name: str = Field(..., min_length=3, max_length=100)
    account_type: AccountType
    account_number: str = Field(..., pattern=r'^\d{9,18}$', description="9-18 digit account number")
    ifsc_code: str = Field(..., pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$', description="IFSC code format: HDFC0001234")
    is_primary: bool = False

#  Create Schema 
class BankAccountCreate(BankAccountBase):
    """Schema for creating a new bank account"""
    pass  # Inherits all fields from Base
#  Update Schema 
class BankAccountUpdate(BaseModel):
    """Schema for updating bank account - only updatable fields"""
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Bank name")
    account_holder_name: Optional[str] = Field(None, min_length=3, max_length=100, description="Account holder name")
    account_type: Optional[AccountType] = None
    ifsc_code: Optional[str] = Field(None, pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$', description="IFSC code")
    is_primary: Optional[bool] = None
    # Note: account_number shouldn't be updatable

class BankAccountCreateResponse(BaseModel):
    """Response after creating a bank account - only server-generated fields"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    is_verified: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime

#  Response Schema 
class BankAccountResponse(BankAccountBase):
    """Schema for bank account data sent to client"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    is_verified: bool
    created_at: datetime
    updated_at: datetime 

#  Verification Schema 
class BankAccountVerify(BaseModel):
    """Schema for verifying bank account"""
    verification_method: str = Field(..., pattern=r'^(PENNY_DROP|BANK_API|MANUAL)$')
    amount_received: Optional[float] = None  # For penny drop verification