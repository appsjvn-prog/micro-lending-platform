from sqlalchemy import Column, String, Enum, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid
from app.core.timezone import utc_now

from app.core.database import Base
from app.models.base import AuditMixin
from app.core.enums import CaseInsensitiveEnum

class AccountType(CaseInsensitiveEnum):
    SAVINGS = "SAVINGS"
    CHECKING = "CHECKING"

class BankAccount(Base, AuditMixin):
    __tablename__ = "bank_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_holder_name = Column(String(100), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    account_number = Column(String(30), unique=True, nullable=False, index=True)
    ifsc_code = Column(String(11), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    # Relationship - connects back to user
    user = relationship("User",foreign_keys="[BankAccount.user_id]", back_populates="bank_accounts")

    

