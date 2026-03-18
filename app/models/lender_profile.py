from sqlalchemy import Column, String, Float, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now

class RiskAppetite(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class LenderStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class LenderProfile(Base):
    __tablename__ = "lender_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business Info
    profile_name = Column(String(100), nullable=True)
    business_type = Column(String(50), nullable=True)  # INDIVIDUAL, COMPANY, TRUST
    
    # Financial Info
    available_balance = Column(Float, default=0.0, nullable=False)
    total_lent = Column(Float, default=0.0, nullable=False)
    
    # Preferences (Loan Offer Defaults)
    default_min_amount = Column(Float, nullable=True)
    default_max_amount = Column(Float, nullable=True)
    default_min_tenure = Column(Integer, nullable=True)
    default_max_tenure = Column(Integer, nullable=True)
    default_interest_rate = Column(Float, nullable=True)
    
    # Risk Profile
    risk_appetite = Column(Enum(RiskAppetite), default=RiskAppetite.MEDIUM)
    
    # Status
    status = Column(Enum(LenderStatus), default=LenderStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = relationship("User", back_populates="lender_profile")
    # loan_offers = relationship("LoanOffer", back_populates="lender", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LenderProfile {self.user_id}>"