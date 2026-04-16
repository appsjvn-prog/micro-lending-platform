"""
Micro Lending Platform - Main Application Entry Point

This module initializes the FastAPI application, configures exception handlers,
and registers all route routers.
"""

# ============================================================================
# STANDARD LIBRARY IMPORTS
# ============================================================================import sys
import sys
import os
import logging
import uuid
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID

# CRITICAL: Force Python to not buffer output
os.environ["PYTHONUNBUFFERED"] = "1"

# Test immediately
print("🔴 CONSOLE TEST - YOU SHOULD SEE THIS", flush=True)
sys.stdout.flush()
print("🔵 ANOTHER TEST", flush=True)

# Third-party imports
from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Local application imports - Core
from app.core.database import engine, Base, get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.timezone import utc_now
from app.core.exceptions import (
    AppException,
    OTPException,
    ValidationException,
    OTPExpiredException,
    OTPInvalidException,
    OTPSendLimitException,
    BankAccountNotFoundException,
    BankAccountAlreadyExistsException,
    BankAccountLimitExceededException,
    PrimaryBankAccountException,
    BankAccountVerificationException,
    LoanProductAlreadyExistsException,
    LoanProductNotFoundException,
    LoanProductValidationException,
    app_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    generic_exception_handler,
    AuthenticationException,
    UserNotFoundException,
    UserInactiveException
)

# Local application imports - Models
from app.models import User, BankAccount, LoanProduct
from app.models.loan_application import LoanApplication
from app.models.loan_offer import LoanOffer
from app.models.loan import Loan
from app.models.otp import OTPPurpose
from app.models.user import UserRole, UserStatus

# Local application imports - Schemas
from app.schemas.user import (
     UserResponse,
     UserRegisterRequest, SetPasswordRequest
)
from app.schemas.bank_account import (
    BankAccountCreate, BankAccountResponse, BankAccountUpdate, BankAccountCreateResponse, BankAccountVerify
)
from app.schemas.loan_product import (
    LoanProductCreate, LoanProductMinimalResponse, 
    LoanProductResponse, LoanProductUpdate
)
from app.schemas.auth import TokenResponse

# Local application imports - Services
from app.services.otp_service import OTPService

# Local application imports - Dependencies
from app.api.dependencies.auth import get_current_user, get_current_admin

# Local application imports - Routers
from app.api.routes import (
    otp, auth, user_profile, address, borrower, 
    lender, loan_offer, loan_application, kyc
)
from app.api.routes.transaction import router as transaction_router
from app.api.routes.loan import router as loan_router


app = FastAPI(
    title="Micro Lending Platform",
    description="API for connecting borrowers with lenders",
    version="1.0.0"
)

# OTP Exceptions
app.add_exception_handler(OTPExpiredException, app_exception_handler)
app.add_exception_handler(OTPInvalidException, app_exception_handler)
app.add_exception_handler(OTPSendLimitException, app_exception_handler)
app.add_exception_handler(OTPException, app_exception_handler)

# Auth Exceptions
app.add_exception_handler(AuthenticationException, app_exception_handler)
app.add_exception_handler(UserNotFoundException, app_exception_handler)
app.add_exception_handler(UserInactiveException, app_exception_handler)

# Bank Account Exceptions
app.add_exception_handler(BankAccountNotFoundException, app_exception_handler)
app.add_exception_handler(BankAccountAlreadyExistsException, app_exception_handler)
app.add_exception_handler(BankAccountLimitExceededException, app_exception_handler)
app.add_exception_handler(PrimaryBankAccountException, app_exception_handler)
app.add_exception_handler(BankAccountVerificationException, app_exception_handler)

# Loan Product Exceptions
app.add_exception_handler(LoanProductNotFoundException, app_exception_handler)
app.add_exception_handler(LoanProductAlreadyExistsException, app_exception_handler)
app.add_exception_handler(LoanProductValidationException, app_exception_handler)

# General Exceptions
app.add_exception_handler(ValidationException, app_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)

# Framework Exceptions
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ---------- Register (NO PASSWORD) ----------
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Registeration"])
def register(
    user: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Step 1: Register with email and phone - BOTH REQUIRED """
    print("\n🔵 REGISTER ENDPOINT HIT")
    print(f"   Email: {user.email}")
    print(f"   Phone: {user.phone}")
    print(f"   Role: {user.role}")

    from app.core.exceptions import (
        AdminCreationException,
        DuplicateResourceException,
        AppException
    )

    # 1.Check if user trying to create admin
    if user.role == UserRole.ADMIN:
        print("   ❌ Admin creation attempt blocked")
        raise AdminCreationException()
    
    try:
        # 2..Check if user exists
        print("   Checking existing user...")
        existing_user = db.query(User).filter(
            (User.email == user.email) | 
            ((User.country_code == user.phone.country_code) & 
             (User.national_number == user.phone.national_number))
        ).first()
        
        if existing_user:
            print(f"   ❌ User already exists: {existing_user.id}")
            if existing_user.email == user.email:
                raise DuplicateResourceException("User", "email", user.email)
            else:
                raise DuplicateResourceException("User", "phone", user.phone.full_number())
        
        # 3.Create new user 
        print("   Creating new user...")
        db_user = User(
            email=user.email,
            country_code=user.phone.country_code,
            national_number=user.phone.national_number,
            role=user.role,
            status=UserStatus.INACTIVE,
            password_hash=None
        )
    
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # OTP Service
        print("   Creating OTP service...")
        otp_service = OTPService(db)
        
        # Send OTP
        print("   Creating OTP...")
        otp = otp_service.create_otp(
            email=user.email,
            phone=user.phone.full_number(),
            purpose=OTPPurpose.REGISTRATION,
            user_id=str(db_user.id)
        )
        
        print(f"   OTP created: {otp.otp_code}")
        print(f"   📱 Would send OTP to {user.phone.full_number()}")
        
        return db_user
        
    except (AdminCreationException, DuplicateResourceException) :
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise AppException(
            f"Registration failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

app.include_router(otp.router)

# ---------- Set Password (After OTP Verification) ----------
@app.post("/auth/set-password", response_model=TokenResponse, tags=["Password Setup"])
def set_password(
    request: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2: Set password after OTP verification
    Activates user account and returns JWT tokens
    """
    
    from app.core.exceptions import (
        InvalidTokenException,
        UserNotFoundException,
        UserAlreadyActiveException,
        PasswordSetupException
    )

    print(f"\n🔑 SET PASSWORD CALLED")

    # Decode and validate temporary token
    try:
        payload = decode_token(request.token)
        print(f"   Decoded payload: {payload}")
        
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id :
            raise InvalidTokenException("Invalid token: missing user ID")
        
        if token_type != "temp":
            raise InvalidTokenException("Invalid token type: Expected temporary token")
            
    except Exception as e:
        print(f"❌ Token error: {str(e)}")
        raise InvalidTokenException(f"Invalid token: {str(e)}")
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundException(user_id)
    
    # Check if already active
    if user.status == "ACTIVE":
        raise UserAlreadyActiveException()
    
    # Validate password match
    if request.password != request.confirm_password:
        raise PasswordSetupException("Passwords do not match")
    
    # Set password and activate user
    try:
        user.set_password(request.password)
        user.status = UserStatus.ACTIVE
        db.commit()
        print(f"    Password set and user activated for {user.email}")
    except Exception as e:
        db.rollback()
        print(f"❌ Database error: {str(e)}")
        raise PasswordSetupException(f"Failed to set password: {str(e)}")
    
    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )

app.include_router(auth.router)
app.include_router(user_profile.router) 
app.include_router(address.router)
app.include_router(borrower.router)
app.include_router(lender.router)
app.include_router(kyc.router)

# ---------- Bank Account Endpoints  ----------

MAX_BANK_ACCOUNTS_PER_USER = 5

def mask_account_number(account_number: str) -> str:
    """Mask account number for display (show last 4 digits)"""
    if len(account_number) > 4:
        return f"XXXX{account_number[-4:]}"
    return account_number

@app.post("/bank-accounts", response_model=BankAccountCreateResponse, status_code=status.HTTP_201_CREATED, tags=["Bank Accounts"])
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
    
    # If this is the first account, make it primary regardless of what was passed
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

@app.get("/bank-accounts", response_model=List[BankAccountResponse], tags=["Bank Accounts"])
def get_my_bank_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank accounts for the current authenticated user"""
    accounts = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).order_by(BankAccount.is_primary.desc(), BankAccount.created_at.asc()).all()
    return accounts


@app.put("/bank-accounts/{account_id}", response_model=BankAccountResponse, tags=["Bank Accounts"])
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
        # Can't unset primary if this is the only account
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

@app.post("/bank-accounts/{account_id}/verify", status_code=status.HTTP_200_OK,summary="Verify Bank Account (admin)", tags=["Bank Accounts"])
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
    if verify_data.verification_method == "PENNY_DROP":
        # In real implementation, you'd verify the penny drop
        # For demo, we'll just mark as verified
        db_account.is_verified = True
    elif verify_data.verification_method == "BANK_API":
        # Integrate with bank API
        db_account.is_verified = True
    elif verify_data.verification_method == "MANUAL":
        # Manual verification by admin
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


@app.delete("/bank-accounts/{account_id}", status_code=status.HTTP_200_OK, tags=["Bank Accounts"])
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
    
     # Check if this is the only account
    account_count = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id
    ).count()
    
    if account_count == 1:
        raise PrimaryBankAccountException("Cannot delete the only bank account. Please add another account first.")
    
    # If deleting the primary account, make another account primary
    was_primary = db_account.is_primary
    
    db.delete(db_account)
    
    # If this was the primary account, set the oldest remaining as primary
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

# ---------- Loan Product Endpoints (Admin Only) ----------
@app.post("/loan-products", response_model=LoanProductMinimalResponse, status_code=status.HTTP_201_CREATED, tags=["Loan Products"])
def create_loan_product(
    product: LoanProductCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin) 
): 
    """Create a new loan product (Admin only)"""

    try:
    # Check if product name exists
        existing = db.query(LoanProduct).filter(LoanProduct.name == product.name).first()
        if existing:
            raise  LoanProductAlreadyExistsException(product.name)
        
        db_product = LoanProduct(
            name=product.name,
            min_amount=product.min_amount,
            max_amount=product.max_amount,
            min_tenure_months=product.min_tenure_months,
            max_tenure_months=product.max_tenure_months,
            interest_type=product.interest_type,
            min_interest_rate=product.min_interest_rate,
            max_interest_rate=product.max_interest_rate,
            repayment_frequency=product.repayment_frequency,
            repayment_day_source=product.repayment_day_source,
            grace_period_days=product.grace_period_days,
            late_fee_percentage=product.late_fee_percentage,
            status=product.status
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return {
            "id": db_product.id,
            "name": db_product.name,
            "status": db_product.status,
            "message": "Loan product created successfully"
        }
    
    except (LoanProductValidationException, LoanProductAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to create loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@app.get("/loan-products", response_model=List[LoanProductResponse], tags=["Loan Products"])
def get_loan_products(
    status: str = None,
    db: Session = Depends(get_db)
    ):
    try:
        """Get all loan products """
        query = db.query(LoanProduct)
        
        if status:
            status = status.upper()
            query = query.filter(LoanProduct.status == status)
        
        return query.all()
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan products: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.get("/loan-products/{product_id}", response_model=LoanProductResponse, tags=["Loan Products"])
def get_loan_product(product_id: str, db: Session = Depends(get_db)):
    """Get loan product by ID (Public - No admin required)"""

    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        if not product:
            raise LoanProductNotFoundException()
        
        return product
    
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.put("/loan-products/{product_id}", response_model=LoanProductResponse, tags=["Loan Products"])
def update_loan_product(
    product_id: str,
    product_update: LoanProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  
):
    print(f"Update data: {product_update.model_dump()}")
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        if product_update.name and product_update.name != db_product.name:
            existing = db.query(LoanProduct).filter(LoanProduct.name == product_update.name).first()
            if existing:
                raise LoanProductAlreadyExistsException(product_update.name)
        
        update_data = product_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_product, field, value)
    
        
        db.commit()
        db.refresh(db_product)
        
        return db_product
    
    except (ValidationException, LoanProductNotFoundException, LoanProductAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to update loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@app.patch("/loan-products/{product_id}/activate", response_model=LoanProductResponse, tags=["Loan Products"])
def activate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  
):
    """Activate a loan product"""
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        db_product.status = "ACTIVE"
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to activate loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@app.patch("/loan-products/{product_id}/deactivate", response_model=LoanProductResponse, tags=["Loan Products"])
def deactivate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin) 
):
    """Deactivate a loan product """
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        db_product.status = "INACTIVE"
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to deactivate loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

app.include_router(loan_offer.router)
app.include_router(loan_application.router)
app.include_router(loan_router)
app.include_router(transaction_router)


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    try:
        # Try to query the user table
        count = db.query(User).count()
        return {"status": "ok", "user_count": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---------- Root Endpoints ----------
@app.get("/")
def root():
    return {
        "message": "Welcome to Micro Lending Platform API",
        "docs": "/docs",
        "redoc": "/redoc"
    }


app.openapi_schema = None  # Clear the cache
app.openapi()  

# Set up logging to file
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )