"""
🔜 WEEK 3 FEATURE - Authentication & OTP
This module is part of the authentication flow.
Not required for Week 2 deliverables (Bank Accounts & Loan Products).
Kept for implementation in Week 3.
"""
from sqlalchemy import Column, String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timedelta

from app.core.database import Base

class OTPPurpose(str, enum.Enum):
    REGISTRATION = "REGISTRATION"
    LOGIN = "LOGIN"
    PASSWORD_RESET = "PASSWORD_RESET"
    BANK_ACCOUNT_VERIFY = "BANK_ACCOUNT_VERIFY"

class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    purpose = Column(Enum(OTPPurpose), nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=5))
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)