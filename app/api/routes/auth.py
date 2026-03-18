from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, decode_token
)
from app.schemas.auth import TokenResponse
from app.models.user import User, UserStatus
from app.core.exceptions import AppException


router = APIRouter(prefix="/auth")

@router.post("/login", response_model=TokenResponse, tags=["AUTHENTICATION"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    print(f"\n🔵 LOGIN ATTEMPT: {form_data.username}")
    
    try:
        # Find user by email
        print("   🔍 Looking up user...")
        user = db.query(User).filter(User.email == form_data.username).first()
        
        if not user:
            raise AppException("Invalid email or password", status_code=401)
        
        print(f"   ✅ User found: {user.id}")
        print(f"   Role: {user.role}, Status: {user.status}")
        
        if not user.password_hash:
            if not user.password_hash:
                raise AppException("Please complete OTP verification and set your password first", status_code=400)
        
        print("   🔐 Verifying password...")
        if not verify_password(form_data.password, user.password_hash):
            print("   ❌ Password incorrect")
            raise AppException("Invalid email or password", status_code=401)
        
        if user.status != "ACTIVE":
            print(f"   ❌ User not active: {user.status}")
            raise AppException("Your account is not active. Please verify your email/phone first.", status_code=403)
        print("   ✅ Password correct, generating tokens...")
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        print(f"   ✅ Login successful for {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user_id=user.id,
            role=user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise  AppException(  
            "An unexpected error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# @router.get("/me", tags=["AUTHENTICATION"])
# def get_current_user_info(
#     current_user: User = Depends(get_current_user)  # ✅ Uses the imported dependency
# ):
#     """Get current authenticated user info"""
#     return {
#         "id": str(current_user.id),
#         "email": current_user.email,
#         "country_code": current_user.country_code,
#         "national_number": current_user.national_number,
#         "role": current_user.role,
#         "status": current_user.status
#     }

# @router.post("/logout", tags=["AUTHENTICATION"])
# def logout():
#     """Logout user - Client should discard the tokens"""
#     return {"message": "Successfully logged out"}