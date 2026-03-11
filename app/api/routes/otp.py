"""
🔜 WEEK 3 FEATURE - OTP Verification Routes
This module handles OTP send/verify/resend functionality.
Not required for Week 2 deliverables (Bank Accounts & Loan Products).
Kept for implementation in Week 3.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string

from app.core.database import get_db
from app.schemas.otp import (
    OTPSendRequest, OTPVerifyRequest, OTPResendRequest,
    OTPSendResponse, OTPVerifyResponse
)
from app.services.otp_service import OTPService
from app.models.user import User,UserStatus
from app.models.otp import OTPPurpose,OTPVerification

router = APIRouter(prefix="/otp", tags=["OTP"])

@router.post("/send", response_model=OTPSendResponse)
async def send_otp(
    request: OTPSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send OTP to email or phone"""
    # Validate based on channel
    if request.channel == "email" and not request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    if request.channel == "phone" and not request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone is required"
        )
    
    otp_service = OTPService(db)
    
    # Check rate limiting (simple check - 3 OTPs per minute)
    recent_otps = db.query(OTPVerification).filter(
        OTPVerification.email == request.email,
        OTPVerification.phone == request.phone,
        OTPVerification.purpose == request.purpose,
        OTPVerification.created_at > datetime.utcnow() - timedelta(minutes=1)
    ).count()
    
    if recent_otps >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again later."
        )
    
    # Create OTP
    otp = otp_service.create_otp(
        email=request.email if request.channel == "email" else None,
        phone=request.phone if request.channel == "phone" else None,
        purpose=request.purpose
    )
    
    # Send OTP
    if request.channel == "email":
        otp_service.send_email_otp(request.email, otp.otp_code, request.purpose, background_tasks)
    else:
        otp_service.send_sms_otp(request.phone, otp.otp_code, request.purpose, background_tasks)
    
    return OTPSendResponse(
        message=f"OTP sent successfully to {request.channel}",
        expires_in=300
    )
@router.post("/verify", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP"""
    print(f"\n🔍 VERIFY OTP CALLED")
    print(f"   Channel: {request.channel}")
    print(f"   Email: {request.email}")
    print(f"   Phone: {request.phone}")
    print(f"   Purpose: {request.purpose}")
    
    # Validate based on channel
    if request.channel == "email" and not request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    if request.channel == "phone" and not request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone is required"
        )
    
    otp_service = OTPService(db)
    
    # Verify OTP
    print(f"🔑 Calling OTP service to verify...")
    is_valid = otp_service.verify_otp(
        email=request.email if request.channel == "email" else None,
        phone=request.phone if request.channel == "phone" else None,
        otp_code=request.otp_code,
        purpose=request.purpose
    )
    
    print(f"✅ OTP Valid: {is_valid}")
    
    if not is_valid:
        print(f"❌ OTP verification failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # ALWAYS activate the user if this is registration
    user_id = None
    if request.purpose == "REGISTRATION" or request.purpose == OTPPurpose.REGISTRATION:
        print(f"🎯 Registration purpose detected - will activate user")
        
        # Find user by email or phone
        user = None
        if request.email:
            print(f"📧 Looking for user with email: {request.email}")
            user = db.query(User).filter(User.email == request.email).first()
        elif request.phone:
            print(f"📱 Looking for user with phone: {request.phone}")
            user = db.query(User).filter(User.phone == request.phone).first()
        
        if user:
            print(f"👤 User found! ID: {user.id}")
            print(f"   Current status: {user.status}")
            print(f"   Current status type: {type(user.status)}")
            
            # Force set to ACTIVE
            user.status = "ACTIVE"  # Use string directly to avoid enum issues
            print(f"   Setting status to: ACTIVE")
            
            db.commit()
            db.refresh(user)
            print(f"✅ User activated! New status: {user.status}")
            user_id = user.id
        else:
            print(f"❌ No user found with that email/phone")
            # List all users to debug
            all_users = db.query(User).all()
            print(f"📋 All users in DB:")
            for u in all_users:
                print(f"   ID: {u.id}, Email: {u.email}, Phone: {u.phone}, Status: {u.status}")
    
    return OTPVerifyResponse(
        verified=True,
        message="OTP verified successfully",
        user_id=user_id
    )

@router.post("/resend", response_model=OTPSendResponse)
async def resend_otp(
    request: OTPResendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend OTP"""
    # Same as send, but with rate limiting check
    if request.channel == "email" and not request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    if request.channel == "phone" and not request.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone is required"
        )
    
    otp_service = OTPService(db)
    
    # Stricter rate limiting for resend
    recent_otps = db.query(OTPVerification).filter(
        OTPVerification.email == request.email,
        OTPVerification.phone == request.phone,
        OTPVerification.purpose == request.purpose,
        OTPVerification.created_at > datetime.utcnow() - timedelta(minutes=2)
    ).count()
    
    if recent_otps >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again later."
        )
    
    # Create new OTP
    otp = otp_service.create_otp(
        email=request.email if request.channel == "email" else None,
        phone=request.phone if request.channel == "phone" else None,
        purpose=request.purpose
    )
    
    # Send OTP
    if request.channel == "email":
        otp_service.send_email_otp(request.email, otp.otp_code, request.purpose, background_tasks)
    else:
        otp_service.send_sms_otp(request.phone, otp.otp_code, request.purpose, background_tasks)
    
    return OTPSendResponse(
        message=f"OTP resent successfully to {request.channel}",
        expires_in=300
    )