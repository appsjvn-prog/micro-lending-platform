
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import uuid

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.bank_account import BankAccount
from app.schemas.bank_account import (
    BankAccountCreate, BankAccountResponse, BankAccountUpdate, 
    BankAccountCreateResponse, BankAccountVerify
)
from app.core.exceptions import (
    ValidationException,
    BankAccountNotFoundException,
    BankAccountAlreadyExistsException,
    BankAccountLimitExceededException,
    PrimaryBankAccountException,
    BankAccountVerificationException
)
from app.core.timezone import utc_now

router = APIRouter(prefix="/bank-accounts", tags=["Bank Accounts"])

MAX_BANK_ACCOUNTS_PER_USER = 5

@router.post("", response_model=BankAccountCreateResponse, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    account: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add bank account for the current authenticated user"""
    
    # Check if account number already exists
    existing = db.query(BankAccount).filter(
        BankAccount.account_number == account.account_number
    ).first()
    
    if existing:
        raise BankAccountAlreadyExistsException()
    
    # Check if user already has any accounts
    existing_accounts = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).count()

    if existing_accounts >= MAX_BANK_ACCOUNTS_PER_USER:
        raise BankAccountLimitExceededException(MAX_BANK_ACCOUNTS_PER_USER)
    
    # Determine if this should be primary
    is_primary = account.is_primary
    
    # If this is the first account, make it primary
    if existing_accounts == 0:
        is_primary = True
    
    # If setting as primary, unset any existing primary
    if is_primary:
        db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id,
            BankAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Create bank account
    db_account = BankAccount(
        user_id=current_user.id,
        bank_name=account.bank_name,
        account_holder_name=account.account_holder_name,
        account_type=account.account_type,
        account_number=account.account_number,
        ifsc_code=account.ifsc_code,
        is_primary=is_primary,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return db_account

@router.get("", response_model=List[BankAccountResponse])
def get_my_bank_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank accounts for the current authenticated user"""
    accounts = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).order_by(BankAccount.is_primary.desc(), BankAccount.created_at.asc()).all()
    return accounts

@router.put("/{account_id}", response_model=BankAccountResponse)
def update_bank_account(
    account_id: str,
    account_update: BankAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bank account"""
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise ValidationException("Invalid account ID format")
    
    db_account = db.query(BankAccount).filter(
        BankAccount.id == account_uuid,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not db_account:
        raise BankAccountNotFoundException()
    
    # Handle primary account update
    if account_update.is_primary:
        other_accounts = db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id,
            BankAccount.id != account_uuid
        ).count()
        
        if other_accounts == 0:
            raise PrimaryBankAccountException("Cannot unset primary account when it's the only account")

        # Unset any existing primary
        db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id,
            BankAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Update only provided fields
    update_data = account_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_account, field, value)
    
    db_account.updated_at = utc_now()
    
    db.commit()
    db.refresh(db_account)
    
    return db_account

@router.post("/{account_id}/verify", status_code=status.HTTP_200_OK)
def verify_bank_account(
    account_id: str,
    verify_data: BankAccountVerify,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Verify a bank account (admin only)"""
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise ValidationException("Invalid account ID format")
    
    db_account = db.query(BankAccount).filter(
        BankAccount.id == account_uuid
    ).first()
    
    if not db_account:
        raise BankAccountNotFoundException()
    
    if db_account.is_verified:
        raise BankAccountVerificationException("Bank account already verified")
    
    # Perform verification based on method
    if verify_data.verification_method in ["PENNY_DROP", "BANK_API", "MANUAL"]:
        db_account.is_verified = True
    
    db_account.updated_at = utc_now()
    db.commit()
    db.refresh(db_account)
    
    return {
        "success": True,
        "message": f"Bank account verified successfully via {verify_data.verification_method}",
        "account_id": str(db_account.id),
        "is_verified": db_account.is_verified
    }

@router.delete("/{account_id}", status_code=status.HTTP_200_OK)
def delete_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bank account"""
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise ValidationException("Invalid account ID format")
    
    db_account = db.query(BankAccount).filter(
        BankAccount.id == account_uuid,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not db_account:
        raise BankAccountNotFoundException()
    
    account_count = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).count()
    
    if account_count == 1:
        raise PrimaryBankAccountException("Cannot delete the only bank account. Please add another account first.")
    
    was_primary = db_account.is_primary
    db.delete(db_account)
    
    if was_primary:
        next_account = db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id
        ).order_by(BankAccount.created_at.asc()).first()
        
        if next_account:
            next_account.is_primary = True
            next_account.updated_at = utc_now()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Bank account deleted successfully"
    }