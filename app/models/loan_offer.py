from sqlalchemy import Column, String, Float, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime, timedelta
from app.core.timezone import utc_now

from app.core.database import Base

class LoanOfferStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INACTIVE = "INACTIVE"

class LoanOffer(Base):
    __tablename__ = "loan_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    loan_product_id = Column(UUID(as_uuid=True), ForeignKey("loan_products.id"), nullable=True)
    
    offer_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    min_amount = Column(Float, nullable=False)
    max_amount = Column(Float, nullable=False)
    min_tenure_months = Column(Integer, nullable=False)
    max_tenure_months = Column(Integer, nullable=False)
    interest_rate = Column(Float, nullable=False)
    preferred_credit_score = Column(Integer, nullable=True)
    preferred_employment_types = Column(String(100), nullable=True)
    status = Column(Enum(LoanOfferStatus), default=LoanOfferStatus.ACTIVE)
    expires_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: utc_now() + timedelta(days=30))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # Relationships - USE STRINGS ONLY, NO IMPORTS
    lender = relationship("User", back_populates="loan_offers")
    loan_product = relationship("LoanProduct")
    applications = relationship("LoanApplication", back_populates="loan_offer")