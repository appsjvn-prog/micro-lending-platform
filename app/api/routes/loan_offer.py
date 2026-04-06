from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from decimal import Decimal

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.lender_profile import LenderProfile
from app.models.borrower_profile import BorrowerProfile
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.schemas.loan_offer import (
    LoanOfferCreate,
    LoanOfferUpdate,
    LoanOfferResponse,
    LoanOfferListResponse,
    LoanOfferMinimalResponse
)
from app.core.timezone import utc_now
from app.core.exceptions import (
    AppException, 
    NotFoundException, 
    UnauthorizedException, 
    ValidationException,
    LoanOfferNotFoundException,
    LoanOfferAlreadyExistsException,
    LoanOfferExpiredException,
    LoanOfferInactiveException  
)

router = APIRouter(prefix="/loan-offers", tags=["Loan Offers"])

# Helper function
def get_verified_lender_or_404(current_user: User, db: Session) -> LenderProfile:
    """Get verified lender profile or raise exception"""
    if current_user.role != "LENDER":
        raise UnauthorizedException("create loan offers")  # 👈 Use UnauthorizedException
    
    lender = db.query(LenderProfile).filter(
        LenderProfile.user_id == current_user.id
    ).first()
    
    if not lender:
        raise NotFoundException("Lender profile")  # 👈 Use NotFoundException
    
    if not lender.is_verified:
        raise UnauthorizedException("create loan offers - your profile must be verified first")  # 👈 Use UnauthorizedException
    
    return lender

@router.post("", response_model=LoanOfferMinimalResponse, status_code=status.HTTP_201_CREATED)
def create_loan_offer(
    offer: LoanOfferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new loan offer"""
    try:
        lender = get_verified_lender_or_404(current_user, db)

        # Check if offer name already exists for this lender
        existing = db.query(LoanOffer).filter(
            LoanOffer.lender_id == current_user.id,
            LoanOffer.offer_name == offer.offer_name
        ).first()
        
        if existing:
            raise LoanOfferAlreadyExistsException(offer.offer_name)
        
        expires_at = utc_now() + timedelta(days=30)

        db_offer = LoanOffer(
            lender_id=current_user.id,
            loan_product_id=offer.loan_product_id,
            offer_name=offer.offer_name,
            description=offer.description,
            min_amount=offer.min_amount,
            max_amount=offer.max_amount,
            min_tenure_months=offer.min_tenure_months,
            max_tenure_months=offer.max_tenure_months,
            interest_rate=offer.interest_rate,
            preferred_credit_score=offer.preferred_credit_score,
            preferred_employment_types=offer.preferred_employment_types,
            expires_at=expires_at,
            status=LoanOfferStatus.ACTIVE
        )
        
        db.add(db_offer)
        db.commit()
        db.refresh(db_offer)
        return {
            "id": db_offer.id,
            "offer_name": db_offer.offer_name,
            "status": db_offer.status,
            "created_at": db_offer.created_at,
            "message": "Loan offer created successfully"
        }
    
    except (UnauthorizedException, NotFoundException, LoanOfferAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to create loan offer: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("", response_model=List[LoanOfferResponse])
def get_loan_offers(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Get loan offers based on role:
    - No token/public: All ACTIVE offers
    - LENDER: Their own offers
    - ADMIN: All offers
    """
    try:
        query = db.query(LoanOffer).options(joinedload(LoanOffer.lender))
        
        if not current_user:
            # Public - only active, not expired
            return query.filter(
                LoanOffer.status == LoanOfferStatus.ACTIVE,
                LoanOffer.expires_at > utc_now()
            ).all()
        
        if current_user.role == "ADMIN":
            # Admin - all offers
            return query.all()
        
        if current_user.role == "LENDER":
            # Lender - their offers
            return query.filter(LoanOffer.lender_id == current_user.id).all()
        
        if current_user.role == "BORROWER":
            # Borrower - filter thier preferences
            return query.filter(
                LoanOffer.status == LoanOfferStatus.ACTIVE,
                LoanOffer.expires_at > utc_now()
            ).order_by(LoanOffer.interest_rate.asc()).limit(50).all()

        return []    
    
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan offers: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{offer_id}", response_model=LoanOfferResponse)
def get_loan_offer_by_id(
    offer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get specific loan offer by ID (public)"""

    try:

        offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
        if not offer:
            raise LoanOfferNotFoundException()
        
        if offer.expires_at and offer.expires_at < utc_now():
            raise LoanOfferExpiredException()
        
        return offer
    
    except (LoanOfferNotFoundException, LoanOfferExpiredException):
        raise
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan offer: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/{offer_id}", response_model=LoanOfferResponse)
def update_loan_offer(
    offer_id: UUID,
    offer_update: LoanOfferUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a loan offer"""

    try:
        offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
        if not offer:
            raise LoanOfferNotFoundException()
        
        if offer.lender_id != current_user.id and current_user.role != "ADMIN":
            raise UnauthorizedException("update this loan offer")
        
        if offer_update.offer_name and offer_update.offer_name != offer.offer_name:
            existing = db.query(LoanOffer).filter(
                LoanOffer.lender_id == offer.lender_id,
                LoanOffer.offer_name == offer_update.offer_name
            ).first()
            if existing:
                raise LoanOfferAlreadyExistsException(offer_update.offer_name)
        
        update_data = offer_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(offer, field, value)
        
        offer.updated_at = utc_now()  
        db.commit()
        db.refresh(offer)
        return offer
    
    except (LoanOfferNotFoundException, UnauthorizedException, LoanOfferAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to update loan offer: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@router.delete("/{offer_id}", status_code=status.HTTP_200_OK)  # 👈 Change to 200 for success message
def deactivate_loan_offer(
    offer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate a loan offer"""
    try:
        offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
        if not offer:
            raise LoanOfferNotFoundException()
        
        if offer.lender_id != current_user.id and current_user.role != "ADMIN":
            raise UnauthorizedException("deactivate this loan offer")
        
        if offer.status == LoanOfferStatus.INACTIVE:
            raise LoanOfferInactiveException()
        
        offer.status = LoanOfferStatus.INACTIVE
        offer.updated_at = utc_now()
        db.commit()
        
        return {
            "success": True,
            "message": "Loan offer deactivated successfully"
        }
    
    except (LoanOfferNotFoundException, UnauthorizedException, LoanOfferInactiveException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to deactivate loan offer: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )