"""
🔜 WEEK 3 FEATURE - OTP Service
This service handles OTP generation and verification for user authentication.
Not required for Week 2 deliverables (Bank Accounts & Loan Products).
Kept for future implementation in Week 3.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from app.models.otp import OTPVerification, OTPPurpose
from app.models.user import User

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
        
        # Create OTP record
        otp = OTPVerification(
            user_id=user_id,
            email=email,
            phone=phone,
            purpose=purpose,
            otp_code=otp_code,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        
        return otp
    
    def verify_otp(self, email: Optional[str], phone: Optional[str], otp_code: str, purpose: OTPPurpose) -> bool:
        """Verify OTP code"""
        # Find valid OTP
        otp = self.db.query(OTPVerification).filter(
            OTPVerification.email == email,
            OTPVerification.phone == phone,
            OTPVerification.purpose == purpose,
            OTPVerification.otp_code == otp_code,
            OTPVerification.is_used == False,
            OTPVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not otp:
            return False
        
        # Mark as used
        otp.is_used = True
        self.db.commit()
        
        return True
    
    def send_email_otp(self, email: str, otp: str, purpose: OTPPurpose, background_tasks: BackgroundTasks):
        """Send OTP via email"""
        # For now, just print to console (we'll implement actual email later)
        print(f"\n📧 EMAIL OTP for {email}: {otp} (Purpose: {purpose})\n")
        
        # TODO: Implement actual email sending using fastapi-mail
        background_tasks.add_task(self._send_email_task, email, otp, purpose)
    
    def send_sms_otp(self, phone: str, otp: str, purpose: OTPPurpose, background_tasks: BackgroundTasks):
        """Send OTP via SMS"""
        # For now, just print to console (we'll implement actual SMS later)
        print(f"\n📱 SMS OTP for {phone}: {otp} (Purpose: {purpose})\n")
        
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
            OTPVerification.expires_at <= datetime.utcnow()
        ).delete()
        self.db.commit()