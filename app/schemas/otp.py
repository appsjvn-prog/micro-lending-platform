from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.otp import OTPPurpose
from app.schemas.user import PhoneNumber

# ---------- Send OTP Request ----------
class OTPSendRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|phone)$", description="Channel to send OTP: email or phone")
    email: Optional[EmailStr] = None
    phone: Optional[PhoneNumber] = None
    purpose: OTPPurpose

    @field_validator('channel')
    def validate_channel_data(cls, v, info):
        """Validate that email/phone is provided based on channel"""
        if v == "email" and not info.data.get('email'):
            raise ValueError("Email is required when channel is email")
        if v == "phone" and not info.data.get('phone'):
            raise ValueError("Phone is required when channel is phone")
        return v

# ---------- Verify OTP Request ----------
class OTPVerifyRequest(BaseModel):
    user_id: UUID
    otp_code: str = Field(..., min_length=4, max_length=6)

# ---------- Resend OTP Request ----------
class OTPResendRequest(BaseModel):
   
    phone: PhoneNumber  # Make required, not optional

# ---------- OTP Response ----------
class OTPSendResponse(BaseModel):
    message: str
    expires_in: int = 300  # 5 minutes in seconds

class OTPVerifyResponse(BaseModel):
    verified: bool
    message: str
    user_id: Optional[UUID] = None
    temp_token: Optional[str] = None  
    access_token: Optional[str] = None