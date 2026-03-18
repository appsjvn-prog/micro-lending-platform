from pydantic import BaseModel, Field, field_validator, EmailStr
from uuid import UUID
from datetime import date, datetime
from typing import Optional

# Import your existing PhoneNumber schema
from app.schemas.user import PhoneNumber
from app.models.user_profile import Gender, MaritalStatus

# Base Schema
class UserProfileBase(BaseModel):
    """Base schema with all user profile fields"""
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    dob: date = Field(..., description="Date of birth")
    gender: Gender
    email: EmailStr
    
    # 👇 Using your existing PhoneNumber schema
    mobile: PhoneNumber
    alternate_mobile: Optional[PhoneNumber] = None
    
    marital_status: Optional[MaritalStatus] = None
    nationality: str = Field(default="Indian", max_length=50)

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name contains only alphabets and spaces"""
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name must contain only alphabets and spaces')
        return v.title()

    @field_validator('dob')
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Validate that user is between 18 and 100 years old"""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        
        if age < 18:
            raise ValueError('User must be at least 18 years old')
        if age > 100:
            raise ValueError('Age cannot be more than 100 years')
        return v

# Create Schema
class UserProfileCreate(UserProfileBase):
    """Schema for creating a user profile"""
    pass

# Update Schema
class UserProfileUpdate(BaseModel):
    """Schema for updating a user profile"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    dob: Optional[date] = None
    gender: Optional[Gender] = None
    email: Optional[EmailStr] = None
    mobile: Optional[PhoneNumber] = None
    alternate_mobile: Optional[PhoneNumber] = None
    marital_status: Optional[MaritalStatus] = None
    nationality: Optional[str] = Field(None, max_length=50)

# Response Schema
class UserProfileResponse(UserProfileBase):
    """Schema for user profile response"""
    id: UUID
    user_id: UUID
    is_active: bool
    profile_completion_pct: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

# Minimal response for creation
class UserProfileMinimalResponse(BaseModel):
    id: UUID
    created_at: datetime
    message: str = "User profile created successfully"

    class Config:
        from_attributes = True