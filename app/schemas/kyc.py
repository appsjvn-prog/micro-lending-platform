from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models.kyc import KYCStatus, KYCDocumentType

#  POST Response Schemas (Minimal) 
class KYCSubmitResponse(BaseModel):
    """Response after submitting KYC"""
    id: UUID
    status: KYCStatus
    created_at: datetime

    class Config:
        from_attributes = True

class KYCDocumentUploadResponse(BaseModel):
    """Response after uploading a document"""
    id: UUID
    doc_type: KYCDocumentType
    uploaded_at: datetime

    class Config:
        from_attributes = True

#  GET Response Schemas 
class KYCDocumentResponse(BaseModel):
    """Document details for GET requests"""
    id: UUID
    doc_type: KYCDocumentType
    uploaded_at: datetime
    is_verified: bool
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True

class KYCMeResponse(BaseModel):
    """User's KYC status (GET /kyc/me)"""
    id: UUID
    status: KYCStatus
    rejection_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    documents: List[KYCDocumentResponse] = []

    class Config:
        from_attributes = True

class KYCAdminDetailResponse(BaseModel):
    """Admin detail view - full KYC with user info"""
    id: UUID
    user_id: UUID
    user_email: str
    user_phone: str
    status: KYCStatus
    rejection_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    documents: List[KYCDocumentResponse] = []

    class Config:
        from_attributes = True

class KYCListResponse(BaseModel):
    """Admin list view - quick summary with counts"""
    id: UUID
    user_id: UUID
    user_email: str
    user_phone: str
    status: KYCStatus
    created_at: datetime
    documents_count: int
    verified_documents_count: int

    class Config:
        from_attributes = True

#  Request Schemas (Input Only) 
class KYCDocumentCreate(BaseModel):
    """What user sends when uploading document"""
    doc_type: KYCDocumentType
    file_url: str = Field(..., max_length=500)

class KYCReviewRequest(BaseModel):
    """What admin sends when reviewing entire KYC"""
    status: KYCStatus
    rejection_reason: Optional[str] = Field(None, max_length=500)

    @field_validator('status')
    def validate_status(cls, v):
        if v not in [KYCStatus.VERIFIED, KYCStatus.REJECTED]:
            raise ValueError('Status must be VERIFIED or REJECTED')
        return v

class KYCDocumentReviewRequest(BaseModel):
    """What admin sends when reviewing a document"""
    is_verified: bool
    rejection_reason: Optional[str] = Field(None, max_length=500)

# Stats 
class KYCStatsResponse(BaseModel):
    """Admin dashboard statistics"""
    total_submissions: int
    pending: int
    verified: int
    rejected: int
    documents_pending: int