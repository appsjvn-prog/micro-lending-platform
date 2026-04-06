from sqlalchemy import Column, ForeignKey, String, Enum, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timezone
from app.models.base import AuditMixin
from app.models.borrower_profile import BorrowerProfile
from app.models.lender_profile import LenderProfile


from app.core.database import Base
from app.core.security import get_password_hash
from app.models.loan_offer import LoanOffer
from app.core.enums import CaseInsensitiveEnum

class UserRole(CaseInsensitiveEnum):
    BORROWER = "BORROWER"
    LENDER = "LENDER"
    ADMIN = "ADMIN"

class UserStatus(CaseInsensitiveEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"

class User(Base, AuditMixin):
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

    profile = relationship("UserProfile", foreign_keys='UserProfile.user_id', back_populates="user", uselist=False)
    borrower_profile = relationship("BorrowerProfile", foreign_keys=[BorrowerProfile.user_id], back_populates="user", uselist=False)
    lender_profile = relationship("LenderProfile", foreign_keys=[LenderProfile.user_id], back_populates="user", uselist=False)
    loan_offers = relationship("LoanOffer", foreign_keys=[LoanOffer.lender_id], back_populates="lender", cascade="all, delete-orphan")
    kyc = relationship("KYC", foreign_keys="[KYC.user_id]", back_populates="user", uselist=False, cascade="all, delete-orphan")
    loan_applications = relationship("LoanApplication", 
                                    foreign_keys="[LoanApplication.borrower_id]",
                                    back_populates="borrower")
    bank_accounts = relationship("BankAccount", 
                                foreign_keys="[BankAccount.user_id]",  # 👈 Add this
                                back_populates="user", 
                                cascade="all, delete-orphan")
    verified_kyc = relationship("KYC", 
                          foreign_keys="[KYC.verified_by]",
                          back_populates="verifier",
                          viewonly=True)

    def set_password(self, password: str):
        """Hash and set password with truncation for bcrypt"""
        # Truncate to 72 bytes if needed (bcrypt limit)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]  # Truncate
        self.password_hash = get_password_hash(password)

