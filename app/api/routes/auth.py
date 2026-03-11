"""
🔜 WEEK 3 FEATURE - Authentication & OTP
This module is part of the authentication flow.
Not required for Week 2 deliverables (Bank Accounts & Loan Products).
Kept for implementation in Week 3.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, decode_token
)
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest
from app.models.user import User, UserStatus
from app.api.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Login & Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    
    - **username**: Your email address
    - **password**: Your password
    """
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # 👇 FIRST: Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # 👇 SECOND: Check if password is set
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password not set. Please complete OTP verification first."
        )
    
    # 👇 THIRD: Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # 👇 FOURTH: Check if user is active
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not active"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role
    )

@router.get("/me")
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user info"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "status": current_user.status
    }

@router.post("/logout")
def logout():
    """
    Logout user
    Note: Client should discard the tokens
    """
    return {"message": "Successfully logged out"}