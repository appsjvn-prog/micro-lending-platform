from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.lender_profile import LenderProfile
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.schemas.loan_offer import (
    LoanOfferCreate,
    LoanOfferUpdate,
    LoanOfferResponse,
    LoanOfferListResponse,
    LoanOfferMinimalResponse
)
from app.core.timezone import utc_now
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException, ValidationException  # 👈 Add imports

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
    lender = get_verified_lender_or_404(current_user, db)
    
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
    
    return []

@router.get("/{offer_id}", response_model=LoanOfferResponse)
def get_loan_offer_by_id(
    offer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get specific loan offer by ID (public)"""
    offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
    if not offer:
        raise NotFoundException("Loan offer")  # 👈 Use NotFoundException
    return offer

@router.put("/{offer_id}", response_model=LoanOfferResponse)
def update_loan_offer(
    offer_id: UUID,
    offer_update: LoanOfferUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a loan offer"""
    offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
    if not offer:
        raise NotFoundException("Loan offer")
    
    if offer.lender_id != current_user.id:
        raise UnauthorizedException("update this loan offer")
    
    update_data = offer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(offer, field, value)
    
    offer.updated_at = utc_now()  # 👈 Use utc_now
    db.commit()
    db.refresh(offer)
    return offer

@router.delete("/{offer_id}", status_code=status.HTTP_200_OK)  # 👈 Change to 200 for success message
def deactivate_loan_offer(
    offer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate a loan offer"""
    offer = db.query(LoanOffer).filter(LoanOffer.id == offer_id).first()
    if not offer:
        raise NotFoundException("Loan offer")
    
    if offer.lender_id != current_user.id:
        raise UnauthorizedException("deactivate this loan offer")
    
    offer.status = LoanOfferStatus.INACTIVE
    offer.updated_at = utc_now()
    db.commit()
    
    return {
        "success": True,
        "message": "Loan offer deactivated successfully"
    }