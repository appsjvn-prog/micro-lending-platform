from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserRegisterRequest, UserResponse
from app.services.otp_service import OTPService
from app.models.otp import OTPPurpose
from app.core.exceptions import (
    AdminCreationException,
    DuplicateResourceException,
    AppException
)

router = APIRouter(prefix="/register",tags=["Registratoin"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Registeration"])
def register(
    user: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """Step 1: Register with email and phone"""

    # 1.Check if user trying to create admin
    if user.role == UserRole.ADMIN:
        raise AdminCreationException()
    
    try:
        # 2.Check if user exists
        existing_user = db.query(User).filter(
            (User.email == user.email) | 
            ((User.country_code == user.phone.country_code) & 
             (User.national_number == user.phone.national_number))
        ).first()
        
        if existing_user:
            if existing_user.email == user.email:
                raise DuplicateResourceException("User", "email", user.email)
            else:
                raise DuplicateResourceException("User", "phone", user.phone.full_number())
        
        # 3.Create new user 
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
        print(f"   Would send OTP to {user.phone.full_number()}")
        
        return db_user
        
    except (AdminCreationException, DuplicateResourceException) :
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Registration failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
