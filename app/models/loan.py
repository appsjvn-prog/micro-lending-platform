from sqlalchemy import Column, ForeignKey, String, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from app.core.database import Base
from app.core.enums import CaseInsensitiveEnum

class LoanStatus(CaseInsensitiveEnum):
    APPROVED = "APPROVED"
    DISBURSED = "DISBURSED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    DEFAULTED = "DEFAULTED"

class Loan(Base):
    __tablename__ = "loans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_application_id = Column(UUID(as_uuid=True), nullable=True)

    borrower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    lender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    principal_amount = Column(Numeric(10, 2), nullable=False)
    tenure_months = Column(Numeric, nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    emi_amount = Column(Numeric(10, 2))
    total_interest = Column(Numeric(10, 2))
    total_repayment = Column(Numeric(10, 2))

    status = Column(SQLEnum(LoanStatus), nullable=False, default=LoanStatus.APPROVED)
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    borrower = relationship("User", foreign_keys=[borrower_id], backref="borrowed_loans")
    lender = relationship("User", foreign_keys=[lender_id], backref="funded_loans")