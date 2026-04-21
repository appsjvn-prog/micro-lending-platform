from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import func
import uuid

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.loan import Loan, LoanStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.schemas.transaction import (
    FlexibleRepaymentAllocation,
    RepaymentRequest,
    RepaymentResponse,
    TransactionResponse,
    FlexibleRepaymentResponse,
    FlexibleRepaymentRequest
)
from app.core.exceptions import(
    NotFoundException,
    ValidationException,
    UnauthorizedException,
    RepaymentValidationException,
    LoanNotDisbursedException,
    AppException
)


from app.models.bank_account import BankAccount
from app.core.timezone import utc_now


router = APIRouter(prefix="/transactions", tags=["Transactions"])

def generate_reference_number(prefix: str) -> str:
    """Generate unique reference number"""
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8].upper()}"


def get_pending_schedules(loan_id: UUID, db: Session):
    """Get all pending schedules ordered by installment number"""
    return db.query(RepaymentSchedule).filter(
        RepaymentSchedule.loan_id == loan_id,
        RepaymentSchedule.status.in_(["PENDING", "PARTIALLY_PAID", "OVERDUE"])
    ).order_by(RepaymentSchedule.installment_number).all()


def calculate_total_remaining(schedules: list) -> Decimal:
    """Calculate total remaining balance including penalties"""
    total = Decimal('0')
    for schedule in schedules:
        remaining = schedule.amount_due - schedule.amount_paid
        penalty = schedule.late_fee_charged if schedule.late_fee_applied else Decimal('0')
        total += remaining + penalty
    return total

@router.post("/loans/{loan_id}", response_model=FlexibleRepaymentResponse, status_code=status.HTTP_201_CREATED)
def make_flexible_repayment(
    loan_id: UUID,
    request: FlexibleRepaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Make loan repayment - Transfer money from borrower to lender
    
    Simple interest: Total repayment is fixed (principal + total interest)
    Each repayment reduces the remaining balance
    """
    try:
        # Get loan
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        if not loan:
            raise NotFoundException("Loan")
        
        # Check if user is borrower or admin
        if current_user.role != "ADMIN" and current_user.id != loan.borrower_id:
            raise UnauthorizedException("make repayments on this loan")
        
        # Check loan status
        if loan.status not in [LoanStatus.DISBURSED, LoanStatus.ACTIVE]:
                if loan.status == LoanStatus.APPROVED:
                    raise LoanNotDisbursedException()
                raise RepaymentValidationException(f"Loan cannot be repaid in {loan.status} status")
        
        # 2. GET PENDING SCHEDULES 
        pending_schedules = get_pending_schedules(loan_id, db)

        if not pending_schedules:
            raise RepaymentValidationException("No pending installments to repay")
        
        # 3. CHECK OVERPAYMENT 

        total_remaining = calculate_total_remaining(pending_schedules)

        if request.amount> total_remaining:
            raise RepaymentValidationException(
                    f"Payment of ₹{request.amount} exceeds remaining balance of ₹{total_remaining}"
                )

        if request.amount <= 0:
            raise RepaymentValidationException("Payment amount must be greater than zero")
        #  4. GET BANK ACCOUNTS 

        borrower_account = db.query(BankAccount).filter(
            BankAccount.user_id == loan.borrower_id,
            BankAccount.is_primary == True
        ).first()
        
        # Get lender's account
        lender_account = db.query(BankAccount).filter(
            BankAccount.user_id == loan.lender_id,
            BankAccount.is_primary == True
        ).first()
        
        # Validate accounts exist
        if not borrower_account or not lender_account:
            raise ValidationException("One or both bank accounts not found")
        
        #  5. PROCESS PAYMENT ACROSS SCHEDULES        remaining_amount = request.amount
        allocations = []

        for schedule in pending_schedules:
            if remaining_amount <= 0:
                break

            penalty = schedule.late_fee_charged if schedule.late_fee_applied else Decimal('0')

            due_amount = (schedule.amount_due - schedule.amount_paid) + penalty

            if remaining_amount >= due_amount:

                payment_amount = due_amount

                schedule.amount_paid = schedule.amount_due
                schedule.status = RepaymentStatus.PAID
                schedule.paid_at = utc_now()

                remaining_amount -= payment_amount

                allocations.append({
                    "installment_number": schedule.installment_number,
                    "amount_paid": payment_amount,
                    "type": "FULL",
                    "penalty_included": 0,
                    "remaining_due": None
                })

            else:

                payment_amount = remaining_amount

                schedule.amount_paid += payment_amount
                schedule.status = RepaymentStatus.PARTIALLY_PAID

                new_remaining = (schedule.amount_due - schedule.amount_paid) + penalty

                allocations.append({
                    "installment_number": schedule.installment_number,
                    "amount_paid": payment_amount,
                    "type": "PARTIAL",
                    "penalty_included": penalty,
                    "remaining_due": new_remaining
                })
                remaining_amount = 0

        # 6. CREATE TRANSACTION RECORD   

        transaction = Transaction(
            id=uuid.uuid4(),
            loan_id=loan_id,
            from_account_id=borrower_account.id,
            to_account_id=lender_account.id,
            amount=request.amount,
            type=TransactionType.REPAYMENT,
            status=TransactionStatus.SUCCESS,
            reference_number=generate_reference_number("FLEX"),
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(transaction)

        #  7. UPDATE LOAN STATUS 

        all_paid = all (s.status == RepaymentStatus.PAID for s in pending_schedules)

        if all_paid:
            loan.status = LoanStatus.CLOSED
            loan.closed_at = utc_now()
            message = "Loan fully repaid and closed"

        else:
            if loan.status == LoanStatus.DISBURSED:
                loan.status = LoanStatus.ACTIVE
            message = f"Payment of ₹{request.amount} processed successfully"

        loan.updated_at = utc_now()

        #  8. COMMIT TO DATABASE 
        db.commit()
        
        #  9. CALCULATE NEW REMAINING BALANCE 

        new_remaining = calculate_total_remaining(pending_schedules)

        # 10. RETURN RESPONSE 
        return FlexibleRepaymentResponse(
            success=True,
            loan_id=str(loan_id),
            payment_amount=float(request.amount),
            amount_allocated=float(request.amount - remaining_amount),
            remaining_balance=float(new_remaining),
            loan_status=loan.status.value,
            transaction_id=str(transaction.id),
            reference_number=transaction.reference_number,
            allocations=[
                FlexibleRepaymentAllocation(
                    installment_number=a["installment_number"],
                    amount_paid=a["amount_paid"],
                    type=a["type"],
                    penalty_included=a["penalty_included"],
                    remaining_due=a["remaining_due"]
                )
                for a in allocations
            ],
            is_loan_fully_paid=all_paid,
            message=message
        )
    
    except (NotFoundException, UnauthorizedException, ValidationException, 
            RepaymentValidationException, LoanNotDisbursedException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to process repayment: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@router.get("/loan/{loan_id}", response_model=List[TransactionResponse])
def get_loan_transactions(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for a loan
    
    - Accessible by: borrower, lender, admin
    """
    try:
        # Get loan
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        if not loan:
            raise NotFoundException("Loan")
        
        # Check permission
        if current_user.role != "ADMIN" and current_user.id not in [loan.borrower_id, loan.lender_id]:
            raise UnauthorizedException("view these transactions")
        
        transactions = db.query(Transaction).filter(
            Transaction.loan_id == loan_id
        ).order_by(Transaction.created_at.desc()).all()
        
        return transactions
    
    except (NotFoundException, UnauthorizedException):
        raise
    except Exception as e:
        raise AppException(
            f"Failed to retrieve transactions: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/user", response_model=List[TransactionResponse])
def get_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get all transactions for current user (as lender or borrower)
    """
    try:
        user_account = db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id
        ).first()
        
        if not user_account:
            return []  
        
        transactions = db.query(Transaction).filter(
            (Transaction.from_account_id == user_account.id) |
            (Transaction.to_account_id == user_account.id)
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        
        return transactions
    
    except Exception as e:
        raise AppException(
            f"Failed to retrieve user transactions: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )