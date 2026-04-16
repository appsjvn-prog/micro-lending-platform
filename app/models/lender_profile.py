from sqlalchemy import Column, Numeric, String, Float, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.core.database import Base
from app.core.timezone import utc_now
from app.models.base import AuditMixin
from app.core.enums import CaseInsensitiveEnum

class RiskAppetite(CaseInsensitiveEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class LenderStatus(CaseInsensitiveEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class LenderProfile(Base, AuditMixin):
    __tablename__ = "lender_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business Info
    profile_name = Column(String(100), nullable=False)
    business_type = Column(String(50), nullable=False)  # INDIVIDUAL, COMPANY, TRUST
    
    # Risk Profile
    risk_appetite = Column(Enum(RiskAppetite), default=RiskAppetite.MEDIUM)
    
    # Status
    status = Column(Enum(LenderStatus), default=LenderStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = relationship("User", back_populates="lender_profile", foreign_keys=[user_id])
    