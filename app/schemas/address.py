from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.address import AddressType  # Import enum from model

# Base Schema - inherits from BaseModel, NOT Base
class AddressBase(BaseModel):
    address_type: AddressType = AddressType.HOME
    is_primary: bool = False
    address_line1: str = Field(..., min_length=5, max_length=100)
    address_line2: Optional[str] = Field(None, max_length=100)
    landmark: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., min_length=2, max_length=50)
    state: str = Field(..., min_length=2, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    pincode: str = Field(..., min_length=6, max_length=10)
    country: str = "India"

# Create Schema
class AddressCreate(AddressBase):
    pass

# Update Schema
class AddressUpdate(BaseModel):
    address_type: Optional[AddressType] = None
    is_primary: Optional[bool] = None
    address_line1: Optional[str] = Field(None, min_length=5, max_length=100)
    address_line2: Optional[str] = Field(None, max_length=100)
    landmark: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    state: Optional[str] = Field(None, min_length=2, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, min_length=6, max_length=10)
    country: Optional[str] = None

# Response Schema
class AddressResponse(AddressBase):
    id: UUID
    user_profile_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True