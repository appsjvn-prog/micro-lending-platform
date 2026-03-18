
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional, Union
from datetime import datetime
from sqlalchemy.orm import joinedload


from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.borrower_profile import BorrowerProfile
from app.models.lender_profile import LenderProfile
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.models.loan_application import LoanApplication, LoanApplicationStatus
from app.schemas.loan_application import (
    LoanApplicationCreate,
    LoanApplicationReview,
    LoanApplicationResponse,
    LoanApplicationMinimalResponse,
    BorrowerLoanApplicationResponse,
    LenderLoanApplicationResponse,
    AdminLoanApplicationResponse,
    LoanApplicationUpdate
)
from app.core.timezone import utc_now
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException, ValidationException


router = APIRouter(prefix="/loan-applications", tags=["Loan Applications"])

# Helper function to check if user is verified borrower
def get_verified_borrower_or_404(current_user: User, db: Session) -> BorrowerProfile:
    """Get verified borrower profile or raise 404"""
    if current_user.role != "BORROWER":
        raise UnauthorizedException("create loan applications")
    
    borrower = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not borrower:
         raise NotFoundException("Borrower profile")
    
    return borrower

@router.post("", response_model=LoanApplicationMinimalResponse, status_code=status.HTTP_201_CREATED)
def create_loan_application(
    application: LoanApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply for a loan offer.
    
    - Requires BORROWER role
    - Can only apply to ACTIVE offers
    - Amount and tenure must be within offer limits
    """
    # Check if user is verified borrower
    borrower = get_verified_borrower_or_404(current_user, db)
    
    # Get the loan offer
    offer = db.query(LoanOffer).filter(LoanOffer.id == application.loan_offer_id).first()
    
    if not offer:
        raise NotFoundException("Loan offer")
    
    # Check if offer is active
    if offer.status != LoanOfferStatus.ACTIVE:
        raise ValidationException("Loan offer is not active")
    
    if offer.expires_at < utc_now():
        raise ValidationException("Loan offer has expired")
    
    # Validate amount and tenure
    if application.requested_amount < offer.min_amount or application.requested_amount > offer.max_amount:
         raise ValidationException(
            f"Amount must be between {offer.min_amount} and {offer.max_amount}"
        )
    
    
    if application.requested_tenure < offer.min_tenure_months or application.requested_tenure > offer.max_tenure_months:
        raise ValidationException(  # 👈 Change to ValidationException
        f"Tenure must be between {offer.min_tenure_months} and {offer.max_tenure_months} months"
    )
    
    # Check if borrower already applied to this offer
    existing = db.query(LoanApplication).filter(
        LoanApplication.loan_offer_id == application.loan_offer_id,
        LoanApplication.borrower_id == current_user.id,
        LoanApplication.status.in_([LoanApplicationStatus.PENDING])
    ).first()
    
    if existing:
        raise ValidationException("You already have a pending application for this offer")
    
    # Create application
    db_application = LoanApplication(
        loan_offer_id=application.loan_offer_id,
        borrower_id=current_user.id,
        requested_amount=application.requested_amount,
        requested_tenure=application.requested_tenure,
        purpose=application.purpose,
        notes=application.notes,
        status=LoanApplicationStatus.PENDING
    )
    
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    return {
        "id": db_application.id,
        "loan_offer_id": db_application.loan_offer_id,
        "status": db_application.status,
        "applied_at": db_application.applied_at,
        "message": "Loan application submitted successfully"
    }

@router.get("", response_model=List[Union[
    BorrowerLoanApplicationResponse,
    LenderLoanApplicationResponse,
    AdminLoanApplicationResponse
]])
def get_loan_applications(
    current_user: Optional[User] = Depends(get_optional_current_user),
    offer_id: Optional[UUID] = Query(None, description="Filter by offer ID"),
    application_id: Optional[UUID] = Query(None, description="Filter by application ID"),  # 👈 ADD THIS
    db: Session = Depends(get_db)
):
    """
    Get loan applications based on role:
    - BORROWER: Their own applications
    - LENDER: Applications to their offers
    - ADMIN: All applications
    - Optional filter by offer_id
    """
    if not current_user:
        return []
    
    # Base query
    query = db.query(LoanApplication).options(
        joinedload(LoanApplication.loan_offer),
        joinedload(LoanApplication.borrower)
    )
    
    # Apply offer filter if provided
    if offer_id:
        query = query.filter(LoanApplication.loan_offer_id == offer_id)

    if application_id:  # 👈 ADD THIS
        query = query.filter(LoanApplication.id == application_id)
    
    # Role-based filtering
    if current_user.role == "ADMIN":
        applications = query.all()
        return [AdminLoanApplicationResponse.model_validate(app) for app in applications]
    
    if current_user.role == "LENDER":
        applications = query.join(
            LoanOffer, LoanApplication.loan_offer_id == LoanOffer.id
        ).filter(
            LoanOffer.lender_id == current_user.id
        ).all()
        return [LenderLoanApplicationResponse.model_validate(app) for app in applications]
    
    if current_user.role == "BORROWER":
        applications = query.filter(
            LoanApplication.borrower_id == current_user.id
        ).all()
        return [BorrowerLoanApplicationResponse.model_validate(app) for app in applications]
    
    return []

@router.put("/{application_id}", response_model=LoanApplicationMinimalResponse)
def update_loan_application(
    application_id: UUID,
    application_update: LoanApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a loan application.
    
    - BORROWER: Can update only amount and tenure (must be within offer limits)
    - ADMIN: Can update interest rate
    """
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    
    if not application:
        raise NotFoundException("Loan application")
    
    # Get the associated offer
    offer = db.query(LoanOffer).filter(
        LoanOffer.id == application.loan_offer_id
    ).first()
    
    # Check permissions
    if current_user.role == "ADMIN":
        # Admin can update interest rate
        if application_update.interest_rate:
            application.interest_rate = application_update.interest_rate
        
        # Admin can also update amount/tenure if needed
        if application_update.requested_amount:
            application.requested_amount = application_update.requested_amount
        
        if application_update.requested_tenure:
            application.requested_tenure = application_update.requested_tenure
    
    elif current_user.role == "BORROWER" and application.borrower_id == current_user.id:
        # 👇 Borrower cannot change interest rate
        if application_update.interest_rate:
            raise UnauthorizedException("You are not allowed to change the interest rate")
        
        # Borrower can update amount and tenure (with validation)
        if application_update.requested_amount:
            if application_update.requested_amount < offer.min_amount or application_update.requested_amount > offer.max_amount:
                raise ValidationException(f"Amount must be between {offer.min_amount} and {offer.max_amount}")
            application.requested_amount = application_update.requested_amount
        
        if application_update.requested_tenure:
            if application_update.requested_tenure < offer.min_tenure_months or application_update.requested_tenure > offer.max_tenure_months:
                raise ValidationException(f"Tenure must be between {offer.min_tenure_months} and {offer.max_tenure_months}")
            application.requested_tenure = application_update.requested_tenure
    
    else:
        raise UnauthorizedException("update this application")
    
    application.updated_at = utc_now()
    db.commit()
    db.refresh(application)
    
    return application

@router.post("/{application_id}/review", response_model=LoanApplicationResponse)
def review_application(
    application_id: UUID,
    review: LoanApplicationReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review a loan application (ACCEPT or REJECT).
    
    - Only the lender who owns the offer can review
    """
    # Get the application
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    
    if not application:
       raise NotFoundException("Application")
    
    # Get the associated offer
    offer = db.query(LoanOffer).filter(LoanOffer.id == application.loan_offer_id).first()
    
    if not offer:
        raise NotFoundException("Associated loan offer")
    
    # Check if current user is the lender
    if offer.lender_id != current_user.id:
        raise UnauthorizedException("Review this application")
    
    # Check if application is in PENDING state
    if application.status != LoanApplicationStatus.PENDING:
        raise ValidationException(f"Application is already {application.status.value}")
    
    # Update application
    application.status = review.status
    application.lender_notes = review.lender_notes
    application.reviewed_at = utc_now()
    application.updated_at = utc_now()
    
    db.commit()
    db.refresh(application)
    
    return application

@router.post("/{application_id}/cancel", response_model=LoanApplicationResponse)
def cancel_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending application.
    
    - Only the borrower who created the application can cancel
    - Can only cancel if status is PENDING
    """
    # Get the application
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    
    if not application:
        raise NotFoundException("Application")
    
    # Check if current user is the borrower
    if application.borrower_id != current_user.id:
        raise UnauthorizedException("cancel this application")
    
    # Check if application is in PENDING state
    if application.status != LoanApplicationStatus.PENDING:
        raise ValidationException(  # 👈 Change to ValidationException
            f"Cannot cancel application with status {application.status.value}"
        )

    # Cancel application
    application.status = LoanApplicationStatus.CANCELLED
    application.updated_at = utc_now()
    
    db.commit()
    db.refresh(application)
    
    return application

