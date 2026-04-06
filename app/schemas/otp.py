from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.otp import OTPPurpose
from app.schemas.user import PhoneNumber

# ---------- Verify OTP Request ----------
class OTPVerifyRequest(BaseModel):
    user_id: UUID
    otp_code: str = Field(..., min_length=4, max_length=6)

# ---------- Resend OTP Request ----------
class OTPResendRequest(BaseModel):
   
    user_id: UUID

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