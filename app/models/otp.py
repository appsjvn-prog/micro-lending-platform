
from sqlalchemy import Column, String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timedelta, timezone

from app.core.database import Base
from app.core.enums import CaseInsensitiveEnum

class OTPPurpose(CaseInsensitiveEnum):
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
    otp_hash = Column(String(255), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, 
                    default=lambda: datetime.now(timezone.utc) + timedelta(minutes=5))