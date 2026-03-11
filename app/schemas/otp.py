from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.otp import OTPPurpose

# ---------- Send OTP Request ----------
class OTPSendRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|phone)$", description="Channel to send OTP: email or phone")
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+\d{10,15}$')
    purpose: OTPPurpose

    def validate_channel_data(self):
        if self.channel == "email" and not self.email:
            raise ValueError("Email is required when channel is email")
        if self.channel == "phone" and not self.phone:
            raise ValueError("Phone is required when channel is phone")
        return self

# ---------- Verify OTP Request ----------
class OTPVerifyRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|phone)$")
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+\d{10,15}$')
    otp_code: str = Field(..., min_length=4, max_length=6)
    purpose: OTPPurpose

# ---------- Resend OTP Request ----------
class OTPResendRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|phone)$")
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+\d{10,15}$')
    purpose: OTPPurpose

# ---------- OTP Response ----------
class OTPSendResponse(BaseModel):
    message: str
    expires_in: int = 300  # 5 minutes in seconds

class OTPVerifyResponse(BaseModel):
    verified: bool
    message: str
    user_id: Optional[UUID] = None
    access_token: Optional[str] = None  # For future JWT implementation