
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
from app.models.user import User, UserStatus
from app.core.timezone import utc_now
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    OTPSendLimitException,
    OTPExpiredException,
    OTPInvalidException
)

router = APIRouter(prefix="/otp", tags=["OTP"])

@router.post("/verify", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP - User identified by user_id"""

    #1. Find User
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise NotFoundException("User")
    
    phone_string = f"{user.country_code}{user.national_number}"
    
    
    #2. Determine purpose from user state
    purpose = OTPPurpose.REGISTRATION if user.status == UserStatus.INACTIVE else OTPPurpose.PASSWORD_RESET

    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_string,
        OTPVerification.purpose == purpose,
        OTPVerification.is_used == False,
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if not otp_record:
        raise OTPInvalidException()
    
    if otp_record.expires_at < utc_now():
        otp_record.is_used = True
        db.commit()
        raise OTPExpiredException()
    
    
    # Verify OTP
    otp_service = OTPService(db)
    is_valid = otp_service.verify_otp(
        phone=phone_string,
        otp_code=request.otp_code,
        purpose=purpose
    )
    
    if not is_valid:
        raise OTPInvalidException()
    
    temp_token = None
    if purpose == OTPPurpose.REGISTRATION:
        temp_token = create_temp_token(
            data={"sub": str(user.id), "purpose": "password_setup"}
        )
        print(f" Temp token generated")
    
    return OTPVerifyResponse(
        verified=True,
        message="OTP verified successfully",
        user_id=user.id,
        temp_token=temp_token,
        access_token=None
    )

@router.post("/resend", response_model=OTPSendResponse)
async def resend_otp(
    request: OTPResendRequest,  
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend OTP - User identified from token"""

    #1. Find User
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise NotFoundException("User")
    
    phone_string = f"{user.country_code}{user.national_number}"
    purpose = OTPPurpose.REGISTRATION if user.status == UserStatus.INACTIVE else OTPPurpose.PASSWORD_RESET  

    # 2.Rate limiting
    otp_service = OTPService(db)

    recent_otps = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_string,
        OTPVerification.purpose == purpose,
        OTPVerification.created_at > utc_now() - timedelta(minutes=2)
    ).count()
    
    if recent_otps >= 5:
        raise OTPSendLimitException(wait_minutes=2)
    
    # Create and send new OTP
    otp = otp_service.create_otp(
        email=user.email,
        phone=phone_string,
        purpose=purpose,
        user_id=str(user.id)
    )
    
    otp_service.send_sms_otp(phone_string, otp.otp_code, purpose, background_tasks)
    
    return OTPSendResponse(
        message="OTP resent successfully",
        expires_in=300
    )