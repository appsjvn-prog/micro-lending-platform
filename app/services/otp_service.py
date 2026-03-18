import random
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from app.models.otp import OTPVerification, OTPPurpose
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.core.timezone import utc_now


class OTPService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def create_otp(self, email: Optional[str], phone: Optional[str], purpose: OTPPurpose, user_id: Optional[str] = None) -> OTPVerification:
        """Create and store new OTP"""
        # Mark any existing unused OTPs as used
        self.db.query(OTPVerification).filter(
            OTPVerification.email == email,
            OTPVerification.phone == phone,
            OTPVerification.purpose == purpose,
            OTPVerification.is_used == False
        ).update({"is_used": True})
        
        # Generate new OTP
        otp_code = self.generate_otp()
        hashed_otp = get_password_hash(otp_code)
        
        # Create OTP record
        otp = OTPVerification(
            user_id=user_id,
            email=email,
            phone=phone,
            purpose=purpose,
            otp_hash=hashed_otp,
            expires_at=utc_now() + timedelta(minutes=5)
        )
        
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        
        # Add plain OTP code for sending (not saved to DB)
        otp.otp_code = otp_code
        
        return otp
    
    def verify_otp(self, phone: str, otp_code: str, purpose: OTPPurpose) -> bool:
        """Verify OTP code using phone only"""
        otp = self.db.query(OTPVerification).filter(
            OTPVerification.phone == phone,
            OTPVerification.purpose == purpose,
            OTPVerification.is_used == False,
            OTPVerification.expires_at > utc_now()
        ).first()
        
        if otp and verify_password(otp_code, otp.otp_hash):
            otp.is_used = True
            self.db.commit()
            return True
        
        return False
    
    def send_email_otp(self, email: str, otp: str, purpose: OTPPurpose, background_tasks: BackgroundTasks):
        """Send OTP via email"""
        # For now, just print to console (we'll implement actual email later)
        print(f"\n📧 EMAIL OTP for {email}: {otp} (Purpose: {purpose})\n")
        print(f"⏰ Expires in 5 minutes")
        
        # TODO: Implement actual email sending using fastapi-mail
        background_tasks.add_task(self._send_email_task, email, otp, purpose)
    
    def send_sms_otp(self, phone: str, otp: str, purpose: OTPPurpose, background_tasks: BackgroundTasks):
        """Send OTP via SMS"""
        # For now, just print to console (we'll implement actual SMS later)
        print(f"\n📱 SMS OTP for {phone}: {otp} (Purpose: {purpose})\n")
        print(f"⏰ Expires in 5 minutes")
        
        # TODO: Implement actual SMS sending using Twilio
        background_tasks.add_task(self._send_sms_task, phone, otp, purpose)
    
    async def _send_email_task(self, email: str, otp: str, purpose: OTPPurpose):
        """Background task for sending email"""
        # TODO: Implement actual email sending
        pass
    
    async def _send_sms_task(self, phone: str, otp: str, purpose: OTPPurpose):
        """Background task for sending SMS"""
        # TODO: Implement actual SMS sending
        pass
    
    def cleanup_expired_otps(self):
        """Delete expired OTPs (run as background job)"""
        self.db.query(OTPVerification).filter(
            OTPVerification.expires_at <= utc_now()
        ).delete()
        self.db.commit()