import pytest
import uuid
from app.models.user import User, UserStatus
from app.core.security import get_password_hash, create_temp_token

def create_test_user(db, email=None, status=UserStatus.ACTIVE, has_password=True):
    """Helper to create test users"""
    if not email:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    user = User(
        id=uuid.uuid4(),
        email=email,
        country_code="+91",
        national_number="9876543210",
        password_hash=get_password_hash("StrongP@ss123") if has_password else None,
        role="BORROWER",
        status=status
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_set_password_success(client, db):
    """Test successful password setup after OTP verification"""
    user = create_test_user(db, has_password=False, status=UserStatus.INACTIVE)
    
    # Create temp token (simulating OTP verification)
    temp_token = create_temp_token(
        data={"sub": str(user.id), "purpose": "password_setup"}
    )
    
    # Set password
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == str(user.id)
    
    # Verify user is now active
    db.refresh(user)
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash is not None

def test_login_success(client, db):
    """Test successful login"""
    user = create_test_user(db)
    
    response = client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == str(user.id)
    assert data["role"] == "BORROWER"

def test_login_wrong_password(client, db):
    """Test login with wrong password"""
    user = create_test_user(db)
    
    response = client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": "WrongPassword123"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    
    # Check response format (could be custom exception or HTTPException)
    if "detail" in data:
        assert "invalid" in data["detail"].lower()
    elif "message" in data:
        assert "invalid" in data["message"].lower()
        assert data["error_code"] == "AUTHENTICATION_FAILED"

def test_login_inactive_user(client, db):
    """Test login with inactive user"""
    user = create_test_user(db, status=UserStatus.INACTIVE)
    
    response = client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 403
    data = response.json()
    
    if "detail" in data:
        assert "inactive" in data["detail"].lower()
    elif "message" in data:
        assert "inactive" in data["message"].lower()
        assert data["error_code"] == "USER_INACTIVE"

def test_login_user_not_found(client, db):
    """Test login with non-existent user"""
    response = client.post(
        "/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    
    if "detail" in data:
        assert "invalid" in data["detail"].lower()
    elif "message" in data:
        assert "invalid" in data["message"].lower()
        assert data["error_code"] == "AUTHENTICATION_FAILED"

def test_login_no_password_set(client, db):
    """Test login when user hasn't set password"""
    user = create_test_user(db, has_password=False, status=UserStatus.INACTIVE)
    
    response = client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": "anypassword"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    if "detail" in data:
        assert "password" in data["detail"].lower() or "otp" in data["detail"].lower()
    elif "message" in data:
        assert "password" in data["message"].lower() or "otp" in data["message"].lower()
        assert data["error_code"] == "AUTHENTICATION_FAILED"