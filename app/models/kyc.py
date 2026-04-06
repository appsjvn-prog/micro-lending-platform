from sqlalchemy import Boolean, Column, String, Enum, ForeignKey, DateTime, Text, UUID as SQLUUID
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now
from app.core.enums import CaseInsensitiveEnum

class KYCStatus(CaseInsensitiveEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class KYCDocumentType(CaseInsensitiveEnum):
    PAN = "PAN"
    AADHAAR = "AADHAAR"
    SALARY_SLIP = "SALARY_SLIP"

class KYC(Base):
    """KYC Request - Main verification record"""
    __tablename__ = "kyc_req"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Status tracking
    status = Column(Enum(KYCStatus), nullable=False, default=KYCStatus.PENDING)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps & audit
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = relationship("User",foreign_keys='[KYC.user_id]', back_populates="kyc")
    documents = relationship("KYCDocument", back_populates="kyc", cascade="all, delete-orphan")
    verifier = relationship("User", foreign_keys='[KYC.verified_by]', back_populates="verified_kyc")
    
    def __repr__(self):
        return f"<KYC {self.user_id} - {self.status.value}>"

class KYCDocument(Base):
    """KYC Documents - Individual documents uploaded"""
    __tablename__ = "kyc_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("kyc_req.id"), nullable=False)
    
    # Document details
    doc_type = Column(Enum(KYCDocumentType), nullable=False)
    file_url = Column(Text, unique=True, nullable=False)
    
    is_verified = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    kyc = relationship("KYC", back_populates="documents")
    
    def __repr__(self):
        return f"<KYCDocument {self.doc_type.value}>"