from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.api.dependencies.auth import verify_admin_header
from app.core.database import engine, Base, get_db
from app.models import User, BankAccount, LoanProduct
from app.schemas.user import UserCreate, UserResponse, UserAdminListResponse, UserAdminDetailResponse
from app.schemas.bank_account import BankAccountCreate, BankAccountResponse ,BankAccountUpdate, BankAccountCreateResponse
from app.schemas.loan_product import LoanProductCreate, LoanProductResponse, LoanProductUpdate  

# 🔜 WEEK 3: OTP and Authentication
# from app.api.routes import otp, auth 

# Create database tables
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Micro Lending Platform",
    description="API for connecting borrowers with lenders",
    version="1.0.0"
)

# 🔜 WEEK 3: OTP and Authentication routes
# app.include_router(otp.router)
# app.include_router(auth.router)


# ---------- User Endpoints (Minimal for Week 2) ----------
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.phone == user.phone)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or phone already exists"
        )
    
    # Create new user 
    db_user = User(
        email=user.email,
        phone=user.phone,
        role=user.role,
        status="ACTIVE"  # Simplified for Week 2 - OTP will handle activation in Week 3
    )
    # 🔜 WEEK 3: Password hashing and OTP verification
    # db_user.set_password(user.password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.get("/users", response_model=List[UserAdminListResponse], tags=["Users"])
def get_users(
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin_header)  
):
    """Get all users - Admin only """
    users = db.query(User).all()
    return users  # Returns full details for admins


@app.get("/users/{user_id}", response_model=UserAdminDetailResponse,tags=["Users"])
def get_user(
    user_id: str, 
    admin: bool = Depends(verify_admin_header),
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

# ---------- Bank Account Endpoints (Week 2 Deliverable) ----------
@app.post("/users/{user_id}/bank-accounts", response_model=BankAccountCreateResponse, status_code=status.HTTP_201_CREATED, tags=["Bank Accounts"])
def create_bank_account(user_id: str, account: BankAccountCreate, db: Session = Depends(get_db)):
    """Add bank account for a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
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
def get_user_bank_accounts(user_id: str, db: Session = Depends(get_db)):
    """Get all bank accounts for a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    accounts = db.query(BankAccount).filter(BankAccount.user_id == user_uuid).all()
    return accounts

@app.put("/bank-accounts/{account_id}", response_model=BankAccountResponse, tags=["Bank Accounts"])
def update_bank_account(
    account_id: str,
    account_update: BankAccountUpdate,
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
    
    print(f"   ✅ Found account. Current values:")
    print(f"      bank_name: {db_account.bank_name}")
    print(f"      is_primary: {db_account.is_primary}")
    
    # Update only provided fields
    update_data = account_update.model_dump(exclude_unset=True)
    print(f"   update_data after exclude_unset: {update_data}")
    
    for field, value in update_data.items():
        print(f"   Setting {field} = {value}")
        setattr(db_account, field, value)
    
    print(f"   After update - bank_name: {db_account.bank_name}")
    print(f"   After update - is_primary: {db_account.is_primary}")
    
    db.commit()
    db.refresh(db_account)
    print(f"   After commit - bank_name: {db_account.bank_name}")
    
    return db_account

@app.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Bank Accounts"])
def delete_bank_account(
    account_id: str,
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
    
    db.delete(db_account)
    db.commit()
    
    return None

# ---------- Loan Product Endpoints (Admin Only - Week 2) ----------
@app.post("/loan-products", response_model=LoanProductResponse, status_code=status.HTTP_201_CREATED, tags=["Loan Products"])
def create_loan_product(
    product: LoanProductCreate, 
    db: Session = Depends(get_db),
    admin: bool = Depends(verify_admin_header)  # 👈 ADMIN ONLY
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
    admin: bool = Depends(verify_admin_header)  # 👈 ADMIN ONLY
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
    admin: bool = Depends(verify_admin_header)  # 👈 ADMIN ONLY
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
    admin: bool = Depends(verify_admin_header)  # 👈 ADMIN ONLY
):
    """Activate a loan product (🔒 ADMIN ONLY - Requires X-Admin-Key header)"""
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
    admin: bool = Depends(verify_admin_header)  # 👈 ADMIN ONLY
):
    """Deactivate a loan product (🔒 ADMIN ONLY - Requires X-Admin-Key header)"""
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