from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re
import phonenumbers  
from typing_extensions import Self
from phonenumbers.phonenumberutil import NumberParseException

from app.models.user import UserRole, UserStatus

# Phone Number Schema
class PhoneNumber(BaseModel):
    """Phone number with separate country code and national number"""
    country_code: str = Field(..., description="Country code with '+', e.g., '+91'")
    national_number: str = Field(..., min_length=4, max_length=15, description="National significant number")

    @field_validator('country_code')
    def validate_country_code(cls, v):
        if not v.startswith('+'):
            raise ValueError('Country code must start with +')
        if len(v) < 2 or len(v) > 5:
            raise ValueError('Invalid country code length')
        return v

    @field_validator('national_number')
    def validate_national_number(cls, v):
        if not v.isdigit():
            raise ValueError('National number must contain only digits')
        return v

    def full_number(self) -> str:
        """Return full E.164 formatted number"""
        return f"{self.country_code}{self.national_number}"

#Base Schema
class UserBase(BaseModel):
    """Base schema with fields common to all user operations"""
    email: EmailStr
    phone: PhoneNumber
    role: UserRole

    @model_validator(mode='after')
    def validate_full_phone(self) -> Self:
        """Validate the complete phone number using phonenumbers"""
        full = self.phone.full_number()
        try:
            parsed = phonenumbers.parse(full)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(f'Invalid phone number: {full}')
        except Exception as e:
            raise ValueError(f'Invalid phone number format: {str(e)}')
        return self

# Update Schema
class UserUpdate(BaseModel):
    """Schema for updating user - all fields optional"""
    email: Optional[EmailStr] = None
    phone: Optional[PhoneNumber] = None
    status: Optional[UserStatus] = None
    
    @model_validator(mode='after')
    def validate_full_phone_if_provided(self) -> Self:
        if self.phone:
            full = self.phone.full_number()
            try:
                parsed = phonenumbers.parse(full)
                if not phonenumbers.is_valid_number(parsed):
                    raise ValueError(f'Invalid phone number: {full}')
            except Exception as e:
                raise ValueError(f'Invalid phone number format: {str(e)}')
        return self

#  Create Schema 
class UserCreate(UserBase):
    """Schema for creating a new user - includes password"""
    password: str = Field(..., min_length=8, max_length=50, description="Password must be 8-50 characters")
    
    @field_validator('password')
    def validate_password(cls, v):
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('Password must be at most 50 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

#  Core Response Schema 
class UserResponse(BaseModel):
    """Schema for user data sent back to client - only server-generated fields"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: UserStatus
    created_at: datetime
    updated_at: datetime

#  Admin List Response 
class UserAdminListResponse(BaseModel):
    """Minimal user info for admin listings"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    status: UserStatus
    created_at: datetime

#  Admin Detail Response 
class UserAdminDetailResponse(BaseModel):
    """Complete user information when admin views specific user"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    phone: PhoneNumber
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

#Register Request Schema
class UserRegisterRequest(BaseModel):
    email: EmailStr
    phone: PhoneNumber
    role: UserRole
    
    @model_validator(mode='after')
    def validate_full_phone(self) -> Self:
        full = self.phone.full_number()
        try:
            parsed = phonenumbers.parse(full,None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(f'Invalid phone number: {full}')
        except NumberParseException as e:
                raise ValueError(f'Invalid phone number format: {str(e)}')
        return self

class SetPasswordRequest(BaseModel):
    """Set password after OTP verification"""
    token: str = Field(..., description="Temporary token from OTP verification")
    password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(..., min_length=8, max_length=50)

    @field_validator('password')
    def validate_password(cls, v):
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('Password must be at most 50 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def validate_passwords_match(self) -> Self: 
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
    
UserRegisterRequest.model_rebuild()
SetPasswordRequest.model_rebuild()    