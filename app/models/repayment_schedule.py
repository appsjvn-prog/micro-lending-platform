from sqlalchemy import Boolean, Column, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from enum import Enum

from app.core.database import Base
from app.core.enums import CaseInsensitiveEnum

class RepaymentStatus(CaseInsensitiveEnum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    PAID_LATE = "PAID_LATE"
    OVERDUE = "OVERDUE"

class RepaymentSchedule(Base):
    __tablename__ = "repayment_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount_due = Column(Numeric(10, 2), nullable=False)
    principal_amount = Column(Numeric(10, 2), nullable=False)
    interest_amount = Column(Numeric(10, 2), nullable=False)

    # Track payments
    amount_paid = Column(Numeric(10, 2), default=0)  # Total paid for this installment
    principal_paid = Column(Numeric(10, 2), default=0)
    interest_paid = Column(Numeric(10, 2), default=0)

    status = Column(SQLEnum(RepaymentStatus), nullable=False, default=RepaymentStatus.PENDING)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Grace period and late fee tracking
    grace_period_days = Column(Integer, default=3)
    late_fee_percentage = Column(Numeric(5, 2), default=2.0)
    late_fee_charged = Column(Numeric(10, 2), default=0)
    late_fee_applied = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def remaining_amount(self):
        """Get remaining amount to be paid for this installment"""
        return self.amount_due - self.amount_paid
    
    @property
    def is_fully_paid(self):
        return self.remaining_amount <= 0
    
    @property
    def principal_remaining(self):
        return self.principal_amount - self.principal_paid
    
    @property
    def interest_remaining(self):
        return self.interest_amount - self.interest_paid