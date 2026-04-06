from typing import Optional

from sqlalchemy import Column, String, Date, Enum, ForeignKey, DateTime, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now
from app.models.base import AuditMixin
from app.core.enums import CaseInsensitiveEnum

# Enum for Gender
class Gender(CaseInsensitiveEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

# Enum for Marital Status
class MaritalStatus(CaseInsensitiveEnum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"

class UserProfile(Base, AuditMixin):
    __tablename__ = "user_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Personal
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    
    # Contact
    email = Column(String(100), unique=True, nullable=False, index=True)
    country_code = Column(String(5), nullable=False)
    national_number = Column(String(15), nullable=False)
    
    alternate_country_code = Column(String(5), nullable=True)
    alternate_national_number = Column(String(15), nullable=True)

    # Additional personal
    marital_status = Column(Enum(MaritalStatus), nullable=True)
    nationality = Column(String(50), default="Indian")
    
    # Status
    is_active = Column(Boolean, default=True)
    profile_completion_pct = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    @property
    def mobile(self) -> dict:
        """Get mobile as PhoneNumber dict for response"""
        return {
            "country_code": self.country_code,
            "national_number": self.national_number
        }

    @mobile.setter
    def mobile(self, value: dict):
        """Set mobile from PhoneNumber dict"""
        self.country_code = value.get("country_code")
        self.national_number = value.get("national_number")

    @property
    def alternate_mobile(self) -> Optional[dict]:
        """Get alternate mobile as PhoneNumber dict"""
        if self.alternate_country_code and self.alternate_national_number:
            return {
                "country_code": self.alternate_country_code,
                "national_number": self.alternate_national_number
            }
        return None

    @alternate_mobile.setter
    def alternate_mobile(self, value: Optional[dict]):
        """Set alternate mobile from PhoneNumber dict"""
        if value is None:
            self.alternate_country_code = None
            self.alternate_national_number = None
        else:
            self.alternate_country_code = value.get("country_code")
            self.alternate_national_number = value.get("national_number")

    # Relationships
    user = relationship("User", foreign_keys="UserProfile.user_id", back_populates="profile")
    addresses = relationship("Address",back_populates="user_profile", cascade="all, delete-orphan")