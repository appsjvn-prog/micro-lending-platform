from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, decode_token
)
from app.schemas.user import SetPasswordRequest
from app.schemas.auth import TokenResponse
from app.models.user import User, UserStatus
from app.core.exceptions import (
    InvalidTokenException,
    AuthenticationException,
    UserNotFoundException,
    UserInactiveException,
    PasswordSetupException,
    UserAlreadyActiveException,
    AppException
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/set-password", response_model=TokenResponse)
def set_password(
    request: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2: Set password after OTP verification
    Activates user account and returns JWT tokens
    """
    
    # Decode and validate temporary token
    try:
        payload = decode_token(request.token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id:
            raise InvalidTokenException("Invalid token: missing user ID")
        
        if token_type != "temp":
            raise InvalidTokenException("Invalid token type: Expected temporary token")
            
    except Exception as e:
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
    except Exception as e:
        db.rollback()
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


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    
    
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise AuthenticationException("Invalid email or password", status_code=401)
    
    print(f"    User found: {user.id}")
    print(f"   Role: {user.role}, Status: {user.status}")
    
    # Check if user has password set
    if not user.password_hash:
        raise AuthenticationException(
            "Please complete OTP verification and set your password first",
            status_code=400
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        print("    Password incorrect")
        raise AuthenticationException("Invalid email or password", status_code=401)
    
    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        print(f"    User not active: {user.status}")
        raise UserInactiveException()
    
    print("    Password correct, generating tokens...")
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    print(f"    Login successful for {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )