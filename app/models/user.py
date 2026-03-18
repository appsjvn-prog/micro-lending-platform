from sqlalchemy import Column, String, Enum, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timezone



from app.core.database import Base
from app.core.security import get_password_hash
from app.models.loan_offer import LoanOffer

class UserRole(str, enum.Enum):
    BORROWER = "BORROWER"
    LENDER = "LENDER"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    country_code = Column(String(5), nullable=False, default="+91")
    national_number = Column(String(15), nullable=False, index=True)
    __table_args__ = (
        UniqueConstraint('country_code', 'national_number', name='unique_phone'),
    )
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.INACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    borrower_profile = relationship("BorrowerProfile", back_populates="user", uselist=False)
    lender_profile = relationship("LenderProfile", back_populates="user", uselist=False)
    loan_offers = relationship("LoanOffer", back_populates="lender", cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Hash and set password with truncation for bcrypt"""
        # Truncate to 72 bytes if needed (bcrypt limit)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]  # Truncate
        self.password_hash = get_password_hash(password)