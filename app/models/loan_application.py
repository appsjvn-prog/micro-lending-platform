from sqlalchemy import Column, Numeric, String, Float, Integer, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.timezone import utc_now

from app.core.database import Base
from app.models.base import AuditMixin  
from app.core.enums import CaseInsensitiveEnum

class LoanApplicationStatus(CaseInsensitiveEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class LoanApplication(Base, AuditMixin):
    __tablename__ = "loan_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_offer_id = Column(UUID(as_uuid=True), ForeignKey("loan_offers.id"), nullable=False)
    borrower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    requested_amount = Column(Numeric(10, 2), nullable=False)
    requested_tenure = Column(Integer, nullable=False)  # in months
    purpose = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(LoanApplicationStatus), default=LoanApplicationStatus.PENDING)
    lender_notes = Column(Text, nullable=True)
    
    applied_at = Column(DateTime(timezone=True), default=utc_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # Relationships - USE STRINGS ONLY, NO IMPORTS
    loan_offer = relationship("LoanOffer", back_populates="applications")
    borrower = relationship("User", 
                           foreign_keys="[LoanApplication.borrower_id]",
                           back_populates="loan_applications")