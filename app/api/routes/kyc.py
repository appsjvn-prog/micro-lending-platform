from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.timezone import utc_now
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User, UserRole
from app.models.kyc import KYC, KYCStatus, KYCDocument
from app.schemas.kyc import (
    KYCSubmitResponse,
    KYCDocumentUploadResponse,
    KYCMeResponse,
    KYCAdminDetailResponse,
    KYCListResponse,
    KYCDocumentCreate,
    KYCReviewRequest,
    KYCDocumentReviewRequest,
    KYCStatsResponse
)
from app.core.exceptions import (
    KYCNotFoundException,
    KYCAlreadyExistsException,
    KYCAlreadyVerifiedException,
    KYCDocumentNotFoundException,
    KYCDocumentAlreadyExistsException,
    KYCNotSubmittedException,
    UnauthorizedException,
    AppException
)



router = APIRouter(prefix="/kyc", tags=["KYC"])

# ---------- UNIFIED REVIEW SCHEMA ----------
class DocumentReviewItem(BaseModel):
    document_id: UUID
    is_verified: bool
    rejection_reason: Optional[str] = None

class KYCUnifiedReviewRequest(BaseModel):
    """Unified review - can handle documents, overall, or both"""
    status: Optional[KYCStatus] = None  # For overall review
    rejection_reason: Optional[str] = None
    documents: Optional[List[DocumentReviewItem]] = None

# ---------- USER ENDPOINTS ----------
@router.post("/submit", response_model=KYCSubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_kyc(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start KYC verification process"""

    try:
    
        existing = db.query(KYC).filter(KYC.user_id == current_user.id).first()
        if existing:
            raise KYCAlreadyExistsException()
        
        kyc = KYC(user_id=current_user.id, status=KYCStatus.PENDING)
        db.add(kyc)
        db.commit()
        db.refresh(kyc)
        
        return kyc
    
    except KYCAlreadyExistsException:
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to submit KYC: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@router.post("/documents", response_model=KYCDocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_kyc_document(
    doc: KYCDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a KYC document"""

    try:
    
        kyc = db.query(KYC).filter(KYC.user_id == current_user.id).first()
        if not kyc:
            raise KYCNotSubmittedException()
        
        if kyc.status == KYCStatus.VERIFIED:
            raise KYCAlreadyVerifiedException()
        
        existing = db.query(KYCDocument).filter(
            KYCDocument.request_id == kyc.id,
            KYCDocument.doc_type == doc.doc_type
        ).first()
        
        if existing:
            # ✅ Allow re-upload if document was rejected
            if existing.rejection_reason:
                # Update existing document with new file
                existing.file_url = doc.file_url
                existing.is_verified = False  # Reset verification status
                existing.rejection_reason = None  # Clear rejection reason
                existing.uploaded_at = utc_now()  # Update timestamp
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Document already uploaded and not rejected
                raise KYCDocumentAlreadyExistsException(doc.doc_type.value)
        
        db_doc = KYCDocument(
            request_id=kyc.id,
            doc_type=doc.doc_type,
            file_url=doc.file_url,
        )
        
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        return db_doc
    
    except (KYCNotSubmittedException, KYCAlreadyVerifiedException, KYCDocumentAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to upload document: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ---------- UNIFIED GET ENDPOINT ----------
@router.get("")
def get_kyc(
    kyc_id: Optional[UUID] = Query(None, description="Get specific KYC by ID"),
    user_id: Optional[UUID] = Query(None, description="Get KYC for specific user"),
    status: Optional[KYCStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KYC information:
    - No params: Get current user's KYC
    - kyc_id: Get specific KYC (admin only)
    - user_id: Get KYC for specific user (admin only)
    - status: Filter by status (admin only)
    """
    try:
    
    # CASE 1: Get specific KYC by ID (admin only)
        if kyc_id:
            if current_user.role != UserRole.ADMIN:
                raise UnauthorizedException("view specific KYC details")
            
            kyc = db.query(KYC).options(
                joinedload(KYC.user),
                joinedload(KYC.documents)
            ).filter(KYC.id == kyc_id).first()
            
            if not kyc:
                raise KYCNotFoundException()
            
            return {
                "id": kyc.id,
                "user_id": kyc.user_id,
                "user_email": kyc.user.email,
                "user_phone": f"{kyc.user.country_code}{kyc.user.national_number}",
                "status": kyc.status,
                "rejection_reason": kyc.rejection_reason,
                "verified_at": kyc.verified_at,
                "verified_by": kyc.verified_by,
                "created_at": kyc.created_at,
                "updated_at": kyc.updated_at,
                "documents": [
                    {
                        "id": d.id,
                        "doc_type": d.doc_type,
                        "uploaded_at": d.uploaded_at,
                        "is_verified": d.is_verified,
                        "rejection_reason": d.rejection_reason
                    }
                    for d in kyc.documents
                ]
            }
        
        # CASE 2: Get KYC for specific user (admin only)
        if user_id:
            if current_user.role != UserRole.ADMIN:
                raise UnauthorizedException("view other user's KYC")
            
            kyc = db.query(KYC).filter(KYC.user_id == user_id).first()
            if not kyc:
                raise KYCNotFoundException()
            
            return {
                "id": kyc.id,
                "user_id": kyc.user_id,
                "status": kyc.status,
                "rejection_reason": kyc.rejection_reason,
                "verified_at": kyc.verified_at,
                "verified_by": kyc.verified_by,
                "created_at": kyc.created_at,
                "updated_at": kyc.updated_at,
                "documents": [
                    {
                        "id": d.id,
                        "doc_type": d.doc_type,
                        "uploaded_at": d.uploaded_at,
                        "is_verified": d.is_verified,
                        "rejection_reason": d.rejection_reason
                    }
                    for d in kyc.documents
                ]
            }
        
        # CASE 3: Admin getting all KYC with filters
        if current_user.role == UserRole.ADMIN:
            query = db.query(KYC).options(
                joinedload(KYC.user),
                joinedload(KYC.documents)
            )
            
            if status:
                query = query.filter(KYC.status == status)
            
            items = query.offset(skip).limit(limit).all()
            
            return [
                {
                    "id": kyc.id,
                    "user_id": kyc.user_id,
                    "user_email": kyc.user.email,
                    "user_phone": f"{kyc.user.country_code}{kyc.user.national_number}",
                    "status": kyc.status,
                    "created_at": kyc.created_at,
                    "documents_count": len(kyc.documents),
                    "verified_documents_count": sum(1 for d in kyc.documents if d.is_verified)
                }
                for kyc in items
            ]
        
        # CASE 4: Regular user getting their own KYC
        kyc = db.query(KYC).options(
            joinedload(KYC.documents)
        ).filter(KYC.user_id == current_user.id).first()
        
        if not kyc:
            raise KYCNotFoundException()
        
        return {
            "id": kyc.id,
            "status": kyc.status,
            "rejection_reason": kyc.rejection_reason,
            "verified_at": kyc.verified_at,
            "created_at": kyc.created_at,
            "documents": [
                {
                    "id": d.id,
                    "doc_type": d.doc_type,
                    "uploaded_at": d.uploaded_at,
                    "is_verified": d.is_verified,
                    "rejection_reason": d.rejection_reason
                }
                for d in kyc.documents
            ]
        }

    except (KYCNotFoundException, UnauthorizedException):
        raise
    except Exception as e:
        raise AppException(
                f"Failed to retrieve KYC: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ---------- UNIFIED REVIEW ENDPOINT ----------
@router.patch("/{kyc_id}/review")
def review_kyc(
    kyc_id: UUID,
    review_data: KYCUnifiedReviewRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Unified KYC review endpoint (admin only).
    
    Can review:
    - Individual documents (pass documents array)
    - Overall KYC (pass status)
    - Both in one call
    
    Auto-updates overall status when all documents are verified.
    """

    try:
    
        kyc = db.query(KYC).options(
            joinedload(KYC.documents)
        ).filter(KYC.id == kyc_id).first()
        
        if not kyc:
            raise KYCNotFoundException()
        
        if kyc.status == KYCStatus.VERIFIED:
            raise KYCAlreadyVerifiedException()
        
        
        response = {
            "kyc_id": kyc.id,
            "updated_documents": [],
            "overall_updated": False
        }
        
        # ========== 1. REVIEW INDIVIDUAL DOCUMENTS ==========
        if review_data.documents:
            for doc_review in review_data.documents:
                doc = db.query(KYCDocument).filter(
                    KYCDocument.id == doc_review.document_id,
                    KYCDocument.request_id == kyc_id
                ).first()
                
                if doc:
                    doc.is_verified = doc_review.is_verified
                    doc.rejection_reason = doc_review.rejection_reason
                    doc.verified_at = utc_now()
                    doc.verified_by = admin.id
                    
                    response["updated_documents"].append({
                        "id": doc.id,
                        "doc_type": doc.doc_type.value,
                        "is_verified": doc.is_verified
                    })
            
            db.commit()
            
            # Check if all documents are now reviewed
            all_docs_have_status = all(
                doc.is_verified is not None or doc.rejection_reason is not None
                for doc in kyc.documents
            )
            
            # Auto-update overall status if all docs reviewed and no explicit status provided
            if all_docs_have_status and not review_data.status:
                all_verified = all(doc.is_verified for doc in kyc.documents)
                if all_verified:
                    kyc.status = KYCStatus.VERIFIED
                    kyc.verified_at = utc_now()
                    kyc.verified_by = admin.id
                    response["overall_updated"] = True
                    response["overall_status"] = "VERIFIED"
                elif any(doc.rejection_reason for doc in kyc.documents):
                    kyc.status = KYCStatus.REJECTED
                    kyc.verified_at = utc_now()
                    kyc.verified_by = admin.id
                    response["overall_updated"] = True
                    response["overall_status"] = "REJECTED"
                
                db.commit()
        
        # ========== 2. REVIEW OVERALL KYC ==========
        if review_data.status:
            if review_data.status not in [KYCStatus.VERIFIED, KYCStatus.REJECTED]:
                raise AppException("Status must be VERIFIED or REJECTED", 400)
            
            kyc.status = review_data.status
            kyc.rejection_reason = review_data.rejection_reason
            kyc.verified_at = utc_now()
            kyc.verified_by = admin.id
            
            # If approving overall, mark all documents as verified
            if review_data.status == KYCStatus.VERIFIED:
                for doc in kyc.documents:
                    doc.is_verified = True
                    doc.verified_at = utc_now()
                    doc.verified_by = admin.id
            
            db.commit()
            response["overall_updated"] = True
            response["overall_status"] = review_data.status.value
        
        response["message"] = "KYC review processed successfully"
        return response
    
    except (KYCNotFoundException, KYCAlreadyVerifiedException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to review KYC: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ---------- STATS (Keep - useful for admin) ----------
@router.get("/stats", response_model=KYCStatsResponse)
def get_kyc_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get KYC statistics (admin only)"""

    try:
    
        total = db.query(KYC).count()
        pending = db.query(KYC).filter(KYC.status == KYCStatus.PENDING).count()
        verified = db.query(KYC).filter(KYC.status == KYCStatus.VERIFIED).count()
        rejected = db.query(KYC).filter(KYC.status == KYCStatus.REJECTED).count()
        
        documents_pending = db.query(KYCDocument).filter(
            KYCDocument.is_verified == False,
            KYCDocument.rejection_reason.is_(None)
        ).count()
        
        return {
            "total_submissions": total,
            "pending": pending,
            "verified": verified,
            "rejected": rejected,
            "documents_pending": documents_pending
        }
    
    except Exception as e:
        raise AppException(
            f"Failed to get KYC stats: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )