from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.loan import Loan, LoanStatus
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.core.timezone import utc_now
from sqlalchemy import func

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.get("", response_model=List[dict])
def get_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[LoanStatus] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get loans based on role:
    - ADMIN: All loans with filters
    - BORROWER: Their own loans
    - LENDER: Loans they funded
    """
    query = db.query(Loan).options(
        joinedload(Loan.borrower),
        joinedload(Loan.lender)
    )
    
    if current_user.role == "ADMIN":
        if status_filter:
            query = query.filter(Loan.status == status_filter)
        
    elif current_user.role == "BORROWER":
        query = query.filter(Loan.borrower_id == current_user.id)
        if status_filter:
            query = query.filter(Loan.status == status_filter)

    elif current_user.role == "LENDER":
        query = query.filter(Loan.lender_id == current_user.id)
        if status_filter:
            query = query.filter(Loan.status == status_filter)
    
    else:
        return []
    
    loans = query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for loan in loans:
        # Calculate repaid amount
        total_repaid = db.query(func.sum(Transaction.amount)).filter(
            Transaction.loan_id == loan.id,
            Transaction.type == TransactionType.REPAYMENT,
            Transaction.status == TransactionStatus.SUCCESS
        ).scalar() or 0
        
        result.append({
            "id": loan.id,
            "borrower_id": loan.borrower_id,
            "lender_id": loan.lender_id,
            "principal_amount": str(loan.principal_amount),
            "tenure_months": loan.tenure_months,
            "interest_rate": float(loan.interest_rate),
            "emi_amount": str(loan.emi_amount) if loan.emi_amount else None,
            "total_interest": str(loan.total_interest) if loan.total_interest else None,
            "total_repayment": str(loan.total_repayment) if loan.total_repayment else None,
            "total_repaid": str(total_repaid),
            "remaining_balance": str(loan.total_repayment - total_repaid) if loan.total_repayment else None,
            "status": loan.status.value,
            "disbursed_at": loan.disbursed_at,
            "closed_at": loan.closed_at,
            "created_at": loan.created_at,
            "updated_at": loan.updated_at
        })
    
    return result


@router.get("/{loan_id}")
def get_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get loan by ID with permission check
    """
    loan = db.query(Loan).options(
        joinedload(Loan.borrower),
        joinedload(Loan.lender),
        joinedload(Loan.borrower).joinedload(User.profile),
        joinedload(Loan.lender).joinedload(User.profile)
    ).filter(Loan.id == loan_id).first()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Check permissions
    if current_user.role != "ADMIN" and current_user.id not in [loan.borrower_id, loan.lender_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view this loan")
    
    # Calculate repaid amount
    total_repaid = db.query(func.sum(Transaction.amount)).filter(
        Transaction.loan_id == loan.id,
        Transaction.type == TransactionType.REPAYMENT,
        Transaction.status == TransactionStatus.SUCCESS
    ).scalar() or 0
    
    # Get repayment schedule
    schedules = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.loan_id == loan.id
    ).order_by(RepaymentSchedule.installment_number).all()
    
    # Get borrower name
    borrower_name = None
    if loan.borrower and loan.borrower.profile:
        borrower_name = f"{loan.borrower.profile.first_name or ''} {loan.borrower.profile.last_name or ''}".strip()
    
    # Get lender name
    lender_name = None
    if loan.lender and loan.lender.profile:
        lender_name = f"{loan.lender.profile.first_name or ''} {loan.lender.profile.last_name or ''}".strip()
    
    return {
        "id": loan.id,
        "loan_application_id": loan.loan_application_id,
        "borrower": {
            "id": loan.borrower_id,
            "name": borrower_name,
            "email": loan.borrower.email if loan.borrower else None
        },
        "lender": {
            "id": loan.lender_id,
            "name": lender_name,
            "email": loan.lender.email if loan.lender else None
        },
        "principal_amount": str(loan.principal_amount),
        "tenure_months": loan.tenure_months,
        "interest_rate": float(loan.interest_rate),
        "emi_amount": str(loan.emi_amount) if loan.emi_amount else None,
        "total_interest": str(loan.total_interest) if loan.total_interest else None,
        "total_repayment": str(loan.total_repayment) if loan.total_repayment else None,
        "total_repaid": str(total_repaid),
        "remaining_balance": str(loan.total_repayment - total_repaid) if loan.total_repayment else None,
        "status": loan.status.value,
        "disbursed_at": loan.disbursed_at,
        "closed_at": loan.closed_at,
        "created_at": loan.created_at,
        "updated_at": loan.updated_at,
        "repayment_schedule": [
            {
                "installment": s.installment_number,
                "due_date": s.due_date.strftime("%Y-%m-%d"),
                "amount_due": str(s.amount_due),
                "principal": str(s.principal_amount),
                "interest": str(s.interest_amount),
                "amount_paid": str(s.amount_paid) if s.amount_paid else "0",
                "status": s.status.value,
                "paid_at": s.paid_at
            }
            for s in schedules
        ]
    }


@router.get("/{loan_id}/schedule")
def get_repayment_schedule(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get repayment schedule for a loan
    """
    # Get loan
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Check permission
    if current_user.role != "ADMIN" and current_user.id not in [loan.borrower_id, loan.lender_id]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get schedule
    schedules = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.loan_id == loan_id
    ).order_by(RepaymentSchedule.installment_number).all()
    
    if not schedules:
        return {"message": "No repayment schedule found", "schedules": []}
    
    # Calculate total repaid
    total_repaid = db.query(func.sum(Transaction.amount)).filter(
        Transaction.loan_id == loan_id,
        Transaction.type == TransactionType.REPAYMENT,
        Transaction.status == TransactionStatus.SUCCESS
    ).scalar() or 0
    
    return {
        "loan_id": str(loan_id),
        "total_repayment": str(loan.total_repayment),
        "total_repaid": str(total_repaid),
        "remaining_balance": str(loan.total_repayment - total_repaid),
        "schedules": [
            {
                "installment": s.installment_number,
                "due_date": s.due_date.strftime("%Y-%m-%d"),
                "amount_due": str(s.amount_due),
                "principal": str(s.principal_amount),
                "interest": str(s.interest_amount),
                "amount_paid": str(s.amount_paid) if s.amount_paid else "0",
                "status": s.status.value,
                "paid_at": s.paid_at.isoformat() if s.paid_at else None,
                "grace_period_days": s.grace_period_days,
                "late_fee_percentage": float(s.late_fee_percentage) if s.late_fee_percentage else None
            }
            for s in schedules
        ]
    }