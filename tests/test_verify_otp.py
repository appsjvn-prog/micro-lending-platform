import pytest
import uuid
from datetime import datetime, timedelta
from app.core.timezone import utc_now
from app.models.otp import OTPVerification, OTPPurpose
from app.models.user import User, UserRole, UserStatus
from app.services.otp_service import OTPService


def test_verify_otp_invalid_code(client, db):
    """Test OTP verification with invalid code"""
    # Create a test user
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=None,
        role=UserRole.BORROWER,
        status=UserStatus.INACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    phone_string = f"{user.country_code}{user.national_number}"
    
    # Create an OTP
    otp_service = OTPService(db)
    otp = otp_service.create_otp(
        email=user.email,
        phone=phone_string,
        purpose=OTPPurpose.REGISTRATION,
        user_id=str(user.id)
    )
    
    # Try with wrong OTP
    response = client.post(
        "/otp/verify",
        json={
            "user_id": str(user.id),
            "otp_code": "999999"  # Wrong code
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    # Check specific OTP exception
    if "success" in data:
        assert data["success"] == False
        assert "invalid" in data["message"].lower()
        assert data["error_code"] == "OTP_INVALID"  # Updated to match
    else:
        assert "detail" in data
        assert "invalid" in data["detail"].lower()


def test_verify_otp_expired(client, db):
    """Test OTP verification with expired OTP"""
    # Create a test user
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=None,
        role=UserRole.BORROWER,
        status=UserStatus.INACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    phone_string = f"{user.country_code}{user.national_number}"
    
    # Create an OTP
    otp_service = OTPService(db)
    otp = otp_service.create_otp(
        email=user.email,
        phone=phone_string,
        purpose=OTPPurpose.REGISTRATION,
        user_id=str(user.id)
    )
    
    # Manually expire the OTP
    otp.expires_at = utc_now() - timedelta(minutes=1)
    db.commit()
    
    # Try to verify expired OTP
    response = client.post(
        "/otp/verify",
        json={
            "user_id": str(user.id),
            "otp_code": otp.otp_code
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "expired" in data["message"].lower()
        assert data["error_code"] == "OTP_EXPIRED"  # Updated to match
    else:
        assert "detail" in data
        assert "expired" in data["detail"].lower()


def test_resend_otp_rate_limit(client, db):
    """Test OTP rate limiting"""
    # Create a test user
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=None,
        role=UserRole.BORROWER,
        status=UserStatus.INACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Try to resend OTP 6 times quickly
    for i in range(6):
        response = client.post(
            "/otp/resend",
            json={
                "user_id": str(user.id)
            }
        )
        
        if i < 5:
            assert response.status_code == 200, f"Request {i+1} should succeed"
        else:
            # 6th request should be rate limited
            assert response.status_code == 400, f"Request {i+1} should fail with rate limit"
            data = response.json()
            
            if "success" in data:
                assert data["success"] == False
                assert "too many" in data["message"].lower()
                # Now matches your exception
                assert data["error_code"] == "OTP_RATE_LIMIT"
            else:
                assert "detail" in data
                assert "too many" in data["detail"].lower()