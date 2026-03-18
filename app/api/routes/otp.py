"""
🔜 WEEK 3 FEATURE - OTP Verification Routes
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.otp import (
    OTPVerifyRequest,
    OTPResendRequest,
    OTPSendResponse, 
    OTPVerifyResponse
)
from app.core.security import create_temp_token
from app.services.otp_service import OTPService
from app.models.otp import OTPPurpose, OTPVerification
from app.models.user import User
from app.core.timezone import utc_now
from app.api.dependencies.auth import get_current_user
from app.core.exceptions import AppException, NotFoundException, ValidationException

router = APIRouter(prefix="/otp", tags=["OTP"])

@router.post("/verify", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP - User identified by user_id"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise NotFoundException("User")
    
    phone_string = f"{user.country_code}{user.national_number}"
    
    
    # Determine purpose from user state
    purpose = OTPPurpose.REGISTRATION if user.status == "INACTIVE" else OTPPurpose.PASSWORD_RESET
    
    otp_service = OTPService(db)
    
    # Verify OTP
    is_valid = otp_service.verify_otp(
        phone=phone_string,
        otp_code=request.otp_code,
        purpose=purpose
    )
    
    if not is_valid:
        raise ValidationException("Invalid or expired OTP")
    
    # Generate temp token if registration
    temp_token = None
    if purpose == OTPPurpose.REGISTRATION:
        temp_token = create_temp_token(
            data={"sub": str(user.id), "purpose": "password_setup"}
        )
        print(f"🔑 Temp token generated")
    
    return OTPVerifyResponse(
        verified=True,
        message="OTP verified successfully",
        user_id=user.id,
        temp_token=temp_token,
        access_token=None
    )

@router.post("/resend", response_model=OTPSendResponse)
async def resend_otp(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),  # 👈 Get user from token
    db: Session = Depends(get_db)
):
    """Resend OTP - User identified from token"""
    
    phone_string = f"{current_user.country_code}{current_user.national_number}"
    purpose = OTPPurpose.REGISTRATION if current_user.status == "INACTIVE" else OTPPurpose.PASSWORD_RESET
    
    otp_service = OTPService(db)
    
    # Rate limiting
    recent_otps = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_string,
        OTPVerification.purpose == purpose,
        OTPVerification.created_at > utc_now() - timedelta(minutes=2)
    ).count()
    
    if recent_otps >= 5:
        raise AppException(  # 👈 Use AppException for rate limiting
            "Too many OTP requests. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Create and send new OTP
    otp = otp_service.create_otp(
        email=current_user.email,
        phone=phone_string,
        purpose=purpose,
        user_id=str(current_user.id)
    )
    
    otp_service.send_sms_otp(phone_string, otp.otp_code, purpose, background_tasks)
    
    return OTPSendResponse(
        message="OTP resent successfully",
        expires_in=300
    )