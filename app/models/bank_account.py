from sqlalchemy import Column, String, Enum, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid
from datetime import datetime,timezone

from app.core.database import Base
class AccountType(str, enum.Enum):
    SAVINGS = "SAVINGS"
    CHECKING = "CHECKING"

class BankAccount(Base):
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship - connects back to user
    user = relationship("User", backref="bank_accounts")