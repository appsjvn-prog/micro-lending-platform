import sys
import os

# CRITICAL: Force Python to not buffer output
os.environ["PYTHONUNBUFFERED"] = "1"

# Force stdout/stderr to be unbuffered
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), 'w', buffering=1)

# Test immediately
print("🔴 CONSOLE TEST - YOU SHOULD SEE THIS", flush=True)
sys.stdout.flush()
print("🔵 ANOTHER TEST", flush=True)

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.services.otp_service import OTPService  
from app.models.otp import OTPPurpose  
from fastapi import BackgroundTasks  

from app.api.dependencies.auth import get_current_user, get_current_admin
from app.core.database import engine, Base, get_db
from app.models import User, BankAccount, LoanProduct
from app.schemas.user import(
     UserCreate, UserResponse, UserAdminListResponse, UserAdminDetailResponse, UserRegisterRequest, SetPasswordRequest
)
from app.schemas.bank_account import (
    BankAccountCreate, BankAccountResponse ,BankAccountUpdate, BankAccountCreateResponse
)
from app.schemas.loan_product import LoanProductCreate, LoanProductResponse, LoanProductUpdate  
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.auth import TokenResponse
from app.api.routes import (
     otp, auth, user_profile, address,  borrower, lender, loan_offer ,loan_application
)
from app.core.exceptions import (
    AppException, app_exception_handler,
    validation_exception_handler,
    integrity_error_handler, sqlalchemy_error_handler
)

import logging
import sys
from fastapi import Request
from fastapi.responses import JSONResponse

# Create database tables
#  Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Micro Lending Platform",
    description="API for connecting borrowers with lenders",
    version="1.0.0"
)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
# app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)

# 🔜 WEEK 3: OTP and Authentication routes
# ---------- STEP 1: Register (NO PASSWORD) ----------
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["REGISTER"])
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
    
    try:
        # Check if user exists
        print("   Checking existing user...")
        existing_user = db.query(User).filter(
            (User.email == user.email) | 
            ((User.country_code == user.phone.country_code) & 
             (User.national_number == user.phone.national_number))
        ).first()
        
        if existing_user:
            print(f"   ❌ User already exists: {existing_user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or phone already exists"
            )
        
        # Create new user
        print("   Creating new user...")
        db_user = User(
            email=user.email,
            country_code=user.phone.country_code,
            national_number=user.phone.national_number,
            role=user.role,
            status="INACTIVE",
            password_hash=None
        )
        
        print(f"   User object created: {db_user}")
        
        db.add(db_user)
        print("   Added to session")
        
        db.commit()
        print("   Committed to database")
        
        db.refresh(db_user)
        print(f"   ✅ User created with ID: {db_user.id}")
        
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
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

app.include_router(otp.router)

# ---------- STEP 4: Set Password (After OTP Verification) ----------
@app.post("/auth/set-password", response_model=TokenResponse, tags=["PASSWORD SETUP"])
def set_password(
    request: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    print(f"\n🔑 SET PASSWORD CALLED")
    
    try:
        payload = decode_token(request.token)
        print(f"   Decoded payload: {payload}")
        
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "temp":
            print(f"❌ Invalid token type: {token_type}")
            raise HTTPException(400, "Invalid token")
            
    except Exception as e:
        print(f"❌ Token error: {str(e)}")
        raise HTTPException(400, f"Invalid token: {str(e)}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    if user.status == "ACTIVE":
        raise HTTPException(400, "User is already active.")
    
    # Set password and activate user
    user.set_password(request.password)
    user.status = "ACTIVE"
    db.commit()
    
    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # ✅ ALWAYS return a valid TokenResponse
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )

app.include_router(auth.router)

@app.get("/users/me", response_model=UserResponse, tags=["Users"])
def get_current_user_info(
    current_user: User = Depends(get_current_user) 
):
    """Get current authenticated user's information"""
    return current_user


@app.get("/users", response_model=List[UserAdminListResponse], tags=["Users"])
def get_users( 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin) 
):
    """Get all users - ADMIN ONLY"""
    users = db.query(User).all()
    return users

@app.get("/users/{user_id}", response_model=UserAdminDetailResponse, tags=["Users"])
def get_user(
    user_id: str, 
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin detail view - complete user information"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    return user   

app.include_router(user_profile.router) 
app.include_router(address.router)
app.include_router(borrower.router)
app.include_router(lender.router)

# ---------- Bank Account Endpoints  ----------
@app.post("/users/{user_id}/bank-accounts", response_model=BankAccountCreateResponse, status_code=status.HTTP_201_CREATED, tags=["Bank Accounts"])
def create_bank_account(
    user_id: str, account: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
 ):
    """Add bank account for a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Check if user exists AND IS THE CURRENT USER
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add bank accounts to your own profile"
        )
    
    # Check if account number already exists
    existing = db.query(BankAccount).filter(
        BankAccount.account_number == account.account_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank account already registered"
        )
    
    # If this is primary, unset any existing primary
    if account.is_primary:
        db.query(BankAccount).filter(
            BankAccount.user_id == user_uuid,
            BankAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Create bank account
    db_account = BankAccount(
        user_id=user_uuid,
        bank_name=account.bank_name,
        account_holder_name=account.account_holder_name,
        account_type=account.account_type,
        account_number=account.account_number,
        ifsc_code=account.ifsc_code,
        is_primary=account.is_primary
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return db_account

@app.get("/users/{user_id}/bank-accounts", response_model=List[BankAccountResponse], tags=["Bank Accounts"])
def get_user_bank_accounts(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all bank accounts for a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    # Ensure uses can only access their own bank accounts
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view bank accounts of other users"
        )

    accounts = db.query(BankAccount).filter(BankAccount.user_id == user_uuid).all()
    return accounts

@app.put("/bank-accounts/{account_id}", response_model=BankAccountResponse, tags=["Bank Accounts"])
def update_bank_account(
    account_id: str,
    account_update: BankAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bank account"""
    print(f"\n🔍 UPDATE BANK ACCOUNT CALLED")
    print(f"   account_id: {account_id}")
    print(f"   update_data received: {account_update.model_dump(exclude_unset=True)}")
    
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        print(f"   ❌ Invalid UUID format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format"
        )
    
    db_account = db.query(BankAccount).filter(BankAccount.id == account_uuid).first()
    
    if not db_account:
        print(f"   ❌ Account not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )

    if db_account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to update this account")
    
    # print(f"   ✅ Found account. Current values:")
    # print(f"      bank_name: {db_account.bank_name}")
    # print(f"      is_primary: {db_account.is_primary}")
    
    # Update only provided fields
    update_data = account_update.model_dump(exclude_unset=True)
    # print(f"   update_data after exclude_unset: {update_data}")
    
    for field, value in update_data.items():
        # print(f"   Setting {field} = {value}")
        setattr(db_account, field, value)
    
    # print(f"   After update - bank_name: {db_account.bank_name}")
    # print(f"   After update - is_primary: {db_account.is_primary}")
    
    db.commit()
    db.refresh(db_account)
    # print(f"   After commit - bank_name: {db_account.bank_name}")
    
    return db_account

@app.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Bank Accounts"])
def delete_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bank account"""
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format"
        )
    
    db_account = db.query(BankAccount).filter(BankAccount.id == account_uuid).first()
    
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )

    if db_account.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to delete this account")
    
    db.delete(db_account)
    db.commit()
    
    return None

# ---------- Loan Product Endpoints (Admin Only) ----------
@app.post("/loan-products", response_model=LoanProductResponse, status_code=status.HTTP_201_CREATED, tags=["Loan Products"])
def create_loan_product(
    product: LoanProductCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  # 👈 ADMIN ONLY
):
    """Create a new loan product (🔒 ADMIN ONLY - Requires X-Admin-Key header)"""
    # Check if product name exists
    existing = db.query(LoanProduct).filter(LoanProduct.name == product.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan product with this name already exists"
        )
    
    db_product = LoanProduct(
        name=product.name,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        min_tenure_months=product.min_tenure_months,
        max_tenure_months=product.max_tenure_months,
        interest_type=product.interest_type,
        min_interest_rate=product.min_interest_rate,
        max_interest_rate=product.max_interest_rate,
        status=product.status
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product

@app.get("/loan-products", response_model=List[LoanProductResponse], tags=["Loan Products"])
def get_loan_products(
    status: str = None,
    # min_amount: float = None,
    # max_amount: float = None,
    db: Session = Depends(get_db)
):
    """Get all loan products """
    query = db.query(LoanProduct)
    
    if status:
        query = query.filter(LoanProduct.status == status)
    # if min_amount:
        # query = query.filter(LoanProduct.max_amount >= min_amount)
    # if max_amount:
        # query = query.filter(LoanProduct.min_amount <= max_amount)
    
    return query.all()

@app.get("/loan-products/{product_id}", response_model=LoanProductResponse, tags=["Loan Products"])
def get_loan_product(product_id: str, db: Session = Depends(get_db)):
    """Get loan product by ID (Public - No admin required)"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    return product

@app.put("/loan-products/{product_id}", response_model=LoanProductResponse, tags=["Loan Products"])
def update_loan_product(
    product_id: str,
    product_update: LoanProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  # 👈 ADMIN ONLY
):
    """Update a loan product (🔒 ADMIN ONLY - Requires X-Admin-Key header)"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    if product_update.name and product_update.name != db_product.name:
        existing = db.query(LoanProduct).filter(LoanProduct.name == product_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loan product with this name already exists"
            )
    
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

@app.delete("/loan-products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Loan Products"])
def delete_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  # 👈 ADMIN ONLY
):
    """Delete a loan product (soft delete) (🔒 ADMIN ONLY - Requires X-Admin-Key header)"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    db_product.status = "INACTIVE"
    db.commit()
    
    return None

@app.patch("/loan-products/{product_id}/activate", response_model=LoanProductResponse, tags=["Loan Products"])
def activate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  # 👈 ADMIN ONLY
):
    """Activate a loan product (🔒 ADMIN ONLY )"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    db_product.status = "ACTIVE"
    db.commit()
    db.refresh(db_product)
    
    return db_product

@app.patch("/loan-products/{product_id}/deactivate", response_model=LoanProductResponse, tags=["Loan Products"])
def deactivate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  # 👈 ADMIN ONLY
):
    """Deactivate a loan product (🔒 ADMIN ONLY r)"""
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )
    
    db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    db_product.status = "INACTIVE"
    db.commit()
    db.refresh(db_product)
    
    return db_product

app.include_router(loan_offer.router)
app.include_router(loan_application.router)

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

@app.get("/health")
def health():
    return {"status": "healthy", "database": "connected"}

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