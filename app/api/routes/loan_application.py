import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional, Union
from decimal import Decimal
from uuid import uuid4
from dateutil.relativedelta import relativedelta

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_optional_current_user
from app.models.user import User, UserRole
from app.models.loan import Loan, LoanStatus
from app.models.loan_product import RepaymentFrequency, LoanProduct
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.models.loan_application import LoanApplication, LoanApplicationStatus
from app.schemas.loan_application import (
    LoanApplicationCreate,
    LoanApplicationReview,
    LoanApplicationResponse,
    LoanApplicationMinimalResponse,
    LoanApplicationUpdate,
    LenderLoanApplicationResponse,
    BorrowerLoanApplicationResponse
)
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.core.timezone import utc_now
from app.core.exceptions import (
    AppException,
    NotFoundException, 
    UnauthorizedException, 
    ValidationException,
    LoanApplicationNotFoundException,
    LoanApplicationAlreadyExistsException,
    LoanApplicationInvalidStatusException,
    LoanApplicationAlreadyReviewedException
)

from app.services.risk_score import RiskScoreCalculator

router = APIRouter(prefix="/loan-applications", tags=["Loan Applications"])

# HELPER FUNCTIONS
def generate_reference_number(prefix: str) -> str:
    """Generate unique reference number"""
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8].upper()}"

def get_verified_borrower_or_404(current_user: User, db: Session) -> BorrowerProfile:
    """Get verified borrower profile or raise 404"""
    if current_user.role != UserRole.BORROWER:
        raise UnauthorizedException("create loan applications")
    
    borrower = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not borrower:
        raise NotFoundException("Borrower profile")
    
    return borrower


def build_admin_response(app: LoanApplication):
    """Build response for admin view with full details"""
    
    borrower = app.borrower
    lender = app.loan_offer.lender if app.loan_offer else None
    borrower_profile = borrower.profile if borrower else None
    lender_profile = lender.profile if lender else None
    
    return {
        "application": {
            "id": app.id,
            "loan_offer_id": app.loan_offer_id,
            "requested_amount": float(app.requested_amount),
            "requested_tenure": app.requested_tenure,
            "status": app.status.value,
            "applied_at": app.applied_at,
            "created_at": app.created_at,
            "reviewed_at": app.reviewed_at,
            "lender_notes": app.lender_notes,
            "purpose": app.purpose,
            "notes": app.notes
        },
        "borrower": {
            "id": borrower.id if borrower else None,
            "email": borrower.email if borrower else None,
            "phone": f"{borrower.country_code}{borrower.national_number}" if borrower else None,
            "name": f"{borrower_profile.first_name} {borrower_profile.last_name}".strip() if borrower_profile else None
        },
        "lender": {
            "id": lender.id if lender else None,
            "email": lender.email if lender else None,
            "name": f"{lender_profile.first_name} {lender_profile.last_name}".strip() if lender_profile else None
        },
        "loan_offer": {
            "id": app.loan_offer.id if app.loan_offer else None,
            "name": app.loan_offer.offer_name if app.loan_offer else None,
            "interest_rate": float(app.loan_offer.interest_rate) if app.loan_offer else None
        }
    }

#CREATE APPLICATION 

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
    try:
        
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
        
        # Validate amount
        if application.requested_amount < offer.min_amount or application.requested_amount > offer.max_amount:
            raise ValidationException(
                f"Amount must be between {offer.min_amount} and {offer.max_amount}"
            )
        
        # Validate tenure
        if application.requested_tenure < offer.min_tenure_months or application.requested_tenure > offer.max_tenure_months:
            raise ValidationException(
                f"Tenure must be between {offer.min_tenure_months} and {offer.max_tenure_months} months"
            )
        
        active_count = db.query(LoanApplication).filter(
        LoanApplication.borrower_id == current_user.id,
        LoanApplication.status == "PENDING"  # Only PENDING, not UNDER_REVIEW
        ).count()

        if active_count >= 3:
            raise AppException(
            f"You already have {active_count} pending applications. "
            "Please wait for them to be processed before applying again.",
            status_code=429
        )

        # Check if borrower already has a pending application for this offer
        existing = db.query(LoanApplication).filter(
            LoanApplication.loan_offer_id == application.loan_offer_id,
            LoanApplication.borrower_id == current_user.id,
            LoanApplication.status == LoanApplicationStatus.PENDING
        ).first()
        
        if existing:
            raise LoanApplicationAlreadyExistsException()
        
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
    
    except (NotFoundException, UnauthorizedException, ValidationException, LoanApplicationAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to create loan application: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


#GET APPLICATIONS 

@router.get("", response_model=List[Union[BorrowerLoanApplicationResponse, LenderLoanApplicationResponse, LoanApplicationResponse]])
def get_loan_applications(
    current_user: Optional[User] = Depends(get_optional_current_user),
    offer_id: Optional[UUID] = Query(None, description="Filter by offer ID"),
    application_id: Optional[UUID] = Query(None, description="Filter by application ID"),
    status: Optional[LoanApplicationStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get loan applications based on role:
    - BORROWER: Their own applications
    - LENDER: Applications to their offers (with borrower details)
    - ADMIN: All applications
    - Optional filters by offer_id, application_id, or status
    """
    try:
        if not current_user:
            return []
        
        # Base query with eager loading of all relationships
        query = db.query(LoanApplication).options(
            joinedload(LoanApplication.loan_offer),
            joinedload(LoanApplication.loan_offer).joinedload(LoanOffer.lender),
            joinedload(LoanApplication.loan_offer).joinedload(LoanOffer.lender).joinedload(User.profile),
            joinedload(LoanApplication.borrower),
            joinedload(LoanApplication.borrower).joinedload(User.profile),
            joinedload(LoanApplication.borrower).joinedload(User.borrower_profile)
        )
        
        # Apply filters
        if offer_id:
            query = query.filter(LoanApplication.loan_offer_id == offer_id)
        if application_id:
            query = query.filter(LoanApplication.id == application_id)
        if status:
            query = query.filter(LoanApplication.status == status)
        
        # Role-based filtering
        if current_user.role == UserRole.ADMIN:
            applications = query.all()
            return [build_admin_response(app) for app in applications]
        
        elif current_user.role == UserRole.LENDER:
            applications = query.join(
                LoanOffer, LoanApplication.loan_offer_id == LoanOffer.id
            ).filter(
                LoanOffer.lender_id == current_user.id
            ).all()
            
            risk_calc = RiskScoreCalculator(db)
            result = []

            for app in applications:
                #Calcualate risk score
                risk_result = risk_calc.calculate_risk_score(str(app.borrower_id), for_lender=True)

                response = LenderLoanApplicationResponse(
                    id=app.id,
                    loan_offer_id=app.loan_offer_id,
                    requested_amount=app.requested_amount,
                    requested_tenure=app.requested_tenure,
                    status=app.status,
                    applied_at=app.applied_at,
                    created_at=app.created_at,
                    borrower_name=f"{app.borrower.profile.first_name} {app.borrower.profile.last_name}".strip() if app.borrower and app.borrower.profile else None,
                    borrower_email=app.borrower.email if app.borrower else None,
                    borrower_phone=f"{app.borrower.country_code}{app.borrower.national_number}" if app.borrower else None,
                    borrower_risk_score=risk_result.get("score") if "error" not in risk_result else None,
                    borrower_risk_level=risk_result.get("risk_level") if "error" not in risk_result else None,
                    purpose=app.purpose,
                    notes=app.notes
                )
                result.append(response)

            return result
        
        elif current_user.role == UserRole.BORROWER:
            applications = query.filter(
                LoanApplication.borrower_id == current_user.id
            ).all()

            result = []
            for app in applications:
                offer = app.loan_offer
                lender = offer.lender if offer else None
                lender_profile = lender.profile if lender else None

                response = BorrowerLoanApplicationResponse(
                    id=app.id,
                    loan_offer_id=app.loan_offer_id,
                    requested_amount=app.requested_amount,
                    requested_tenure=app.requested_tenure,
                    status=app.status,
                    applied_at=app.applied_at,
                    created_at=app.created_at,
                    offer_name=offer.offer_name if offer else None,
                    lender_name=f"{lender_profile.first_name} {lender_profile.last_name}".strip() if lender_profile else None,
                    interest_rate=offer.interest_rate if offer else None
                )
                result.append(response)
            return result
        
        return []
    
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan applications: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# UPDATE APPLICATION 

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
    - ADMIN: Can update amount and tenure
    """
    try:

        application = db.query(LoanApplication).filter(
            LoanApplication.id == application_id
        ).first()
        
        if not application:
            raise LoanApplicationNotFoundException()
        
        # Only allow update if status is PENDING
        if application.status != LoanApplicationStatus.PENDING:
            raise LoanApplicationInvalidStatusException(
                application.status.value, 
                [LoanApplicationStatus.PENDING.value]
            )
        
        # Get the associated offer
        offer = db.query(LoanOffer).filter(
            LoanOffer.id == application.loan_offer_id
        ).first()
        
        if not offer:
            raise NotFoundException("Associated loan offer")
        
        updated = False
        
        # Check permissions
        if current_user.role == UserRole.ADMIN:
            # Admin can update amount/tenure
            if application_update.requested_amount:
                application.requested_amount = application_update.requested_amount
                updated = True
            if application_update.requested_tenure:
                application.requested_tenure = application_update.requested_tenure
                updated = True
        
        elif current_user.role == UserRole.BORROWER and application.borrower_id == current_user.id:
            # Borrower can update amount and tenure (with validation)
            if application_update.requested_amount:
                if application_update.requested_amount < offer.min_amount or application_update.requested_amount > offer.max_amount:
                    raise ValidationException(f"Amount must be between {offer.min_amount} and {offer.max_amount}")
                application.requested_amount = application_update.requested_amount
                updated = True
            
            if application_update.requested_tenure:
                if application_update.requested_tenure < offer.min_tenure_months or application_update.requested_tenure > offer.max_tenure_months:
                    raise ValidationException(f"Tenure must be between {offer.min_tenure_months} and {offer.max_tenure_months}")
                application.requested_tenure = application_update.requested_tenure
                updated = True
        
        else:
            raise UnauthorizedException("update this application")
        
        if not updated:
            raise ValidationException("No fields to update")
        
        application.updated_at = utc_now()
        db.commit()
        db.refresh(application)
        
        return {
            "id": application.id,
            "loan_offer_id": application.loan_offer_id,
            "status": application.status,
            "applied_at": application.applied_at,
            "message": "Loan application updated successfully"
        }
    
    except (LoanApplicationNotFoundException, LoanApplicationInvalidStatusException, 
            NotFoundException, ValidationException, UnauthorizedException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to update loan application: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# REVIEW APPLICATION (LENDER) 
@router.post("/{application_id}/review", response_model=LoanApplicationResponse)
def review_application(
    application_id: UUID,
    review: LoanApplicationReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review a loan application (ACCEPT or REJECT).
    
    If ACCEPTED:
        - Creates loan automatically
        - Disburses money automatically (disbursement date = today)
        - Generates repayment schedule automatically
        - Only the lender who owns the offer can do this
    """

    try:
        # Get the application
        application = db.query(LoanApplication).options(
            joinedload(LoanApplication.loan_offer),
            joinedload(LoanApplication.borrower)
        ).filter(
            LoanApplication.id == application_id
        ).first()
        
        if not application:
            raise LoanApplicationNotFoundException()
        
        offer = application.loan_offer
        
        if not offer:
            raise NotFoundException("Associated loan offer")
        
        # Check if current user is the lender
        if offer.lender_id != current_user.id and current_user.role != "ADMIN":
            raise UnauthorizedException("Only the lender can review this application")
        
        # Check if application is in PENDING state
        if application.status != LoanApplicationStatus.PENDING:
            raise LoanApplicationAlreadyReviewedException()
        
        # Update application
        application.status = review.status
        application.lender_notes = review.lender_notes
        application.reviewed_at = utc_now()
        application.updated_at = utc_now()
        
        # If REJECTED, just save and return
        if review.status != LoanApplicationStatus.ACCEPTED:

            db.commit()
            db.refresh(application)
            return application
        
        MAX_ACTIVE_LOANS = 2

        active_loans_count = db.query(Loan).filter(
            Loan.borrower_id == application.borrower_id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.DISBURSED])
        ).count()

        if active_loans_count >= MAX_ACTIVE_LOANS:
            # Auto-reject the application
            application.status = LoanApplicationStatus.REJECTED
            application.lender_notes = f"Auto-rejected: Borrower already has {active_loans_count} active loans (max {MAX_ACTIVE_LOANS})"
            application.reviewed_at = utc_now()
            application.updated_at = utc_now()
            db.commit()
            
            raise ValidationException(
                f"Borrower already has {active_loans_count} active loans. "
                f"Maximum {MAX_ACTIVE_LOANS} active loans allowed per borrower."
            )
        
        # ACCEPTED: Create Loan, Disburse, Generate Schedule 
        
        # Calculate loan details (simple interest)
        total_interest = application.requested_amount * (Decimal(str(offer.interest_rate)) / 100) * (Decimal(application.requested_tenure) / 12)
        total_repayment = application.requested_amount + total_interest
        emi = total_repayment / application.requested_tenure
        
        disbursement_date = utc_now()
        
        # Create loan
        loan = Loan(
            id=uuid4(),
            loan_application_id=application.id,
            borrower_id=application.borrower_id,
            lender_id=offer.lender_id,
            principal_amount=application.requested_amount,
            tenure_months=application.requested_tenure,
            interest_rate=offer.interest_rate,
            emi_amount=emi.quantize(Decimal('0.01')),
            total_interest=total_interest.quantize(Decimal('0.01')),
            total_repayment=total_repayment.quantize(Decimal('0.01')),
            status=LoanStatus.ACTIVE,  # or LoanStatus.DISBURSED - your choice
            disbursed_at=disbursement_date
        )
        
        db.add(loan)
        db.flush()  # Get loan.id
        
        # Create disbursement transaction (always SUCCESS)
        transaction = Transaction(
            loan_id=loan.id,
            from_account_id=offer.lender_id,  # Using user_id as account for simplicity
            to_account_id=application.borrower_id,
            amount=loan.principal_amount,
            type=TransactionType.DISBURSEMENT,
            status=TransactionStatus.SUCCESS,
            reference_number=generate_reference_number("DISB"),
            created_at=disbursement_date,
            updated_at=disbursement_date
        )
        
        db.add(transaction)
        
        # Get product config for schedule
        product = db.query(LoanProduct).filter(
            LoanProduct.id == offer.loan_product_id
        ).first()
        
        # Generate repayment schedule
        from dateutil.relativedelta import relativedelta
        
        if product and product.repayment_frequency == RepaymentFrequency.MONTHLY:
            monthly_interest = loan.total_interest / loan.tenure_months
            monthly_principal = loan.principal_amount / loan.tenure_months
            
            schedules = []
            for i in range(1, loan.tenure_months + 1):
                due_date = disbursement_date.date() + relativedelta(months=i)
                
                schedule = RepaymentSchedule(
                    loan_id=loan.id,
                    installment_number=i,
                    due_date=due_date,
                    amount_due=emi.quantize(Decimal('0.01')),
                    principal_amount=monthly_principal.quantize(Decimal('0.01')),
                    interest_amount=monthly_interest.quantize(Decimal('0.01')),
                    status=RepaymentStatus.PENDING,
                    grace_period_days=product.grace_period_days if product else 3,
                    late_fee_percentage=product.late_fee_percentage if product else 2.0
                )
                schedules.append(schedule)
                db.add(schedule)
            
            # Adjust last installment for rounding
            total_principal = sum(s.principal_amount for s in schedules)
            if total_principal != loan.principal_amount:
                diff = loan.principal_amount - total_principal
                schedules[-1].principal_amount += diff
                schedules[-1].amount_due = schedules[-1].principal_amount + schedules[-1].interest_amount
                schedules[-1].amount_due = schedules[-1].amount_due.quantize(Decimal('0.01'))
        
        db.commit()
        db.refresh(loan)
        
        return application
    
    except (LoanApplicationNotFoundException, NotFoundException, UnauthorizedException, 
            LoanApplicationAlreadyReviewedException, ValidationException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to review loan application: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
#  CANCEL APPLICATION (BORROWER) 

@router.post("/{application_id}/cancel", response_model=LoanApplicationMinimalResponse)
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
    try:

        # Get the application
        application = db.query(LoanApplication).filter(
            LoanApplication.id == application_id
        ).first()
        
        if not application:
            raise LoanApplicationNotFoundException()
        
        # Check if current user is the borrower
        if application.borrower_id != current_user.id:
            raise UnauthorizedException("cancel this application")
        
        # Check if application is in PENDING state
        if application.status != LoanApplicationStatus.PENDING:
            raise LoanApplicationInvalidStatusException(
                application.status.value,
                [LoanApplicationStatus.PENDING.value]
            )
        
        # Cancel application
        application.status = LoanApplicationStatus.CANCELLED
        application.updated_at = utc_now()
        
        db.commit()
        db.refresh(application)
        
        return {
            "id": application.id,
            "loan_offer_id": application.loan_offer_id,
            "status": application.status,
            "applied_at": application.applied_at,
            "message": "Loan application cancelled successfully"
        }
    
    except (LoanApplicationNotFoundException, UnauthorizedException, LoanApplicationInvalidStatusException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to cancel loan application: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )