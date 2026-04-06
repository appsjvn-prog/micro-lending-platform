from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from enum import Enum

from app.core.database import Base
from app.core.enums import CaseInsensitiveEnum

class TransactionType(CaseInsensitiveEnum):
    DISBURSEMENT = "DISBURSEMENT"
    REPAYMENT = "REPAYMENT"
    REFUND = "REFUND"

class TransactionStatus(CaseInsensitiveEnum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False)
    from_account_id = Column(UUID(as_uuid=True), nullable=False)
    to_account_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.INITIATED)
    failure_reason = Column(Text, nullable=True)
    reference_number = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())