import pytest
import uuid
from datetime import datetime, timedelta
from app.core.security import create_temp_token, decode_token
from app.models.user import User, UserStatus
from app.core.timezone import utc_now

@pytest.fixture
def test_inactive_user(db):
    """Create an inactive test user without password"""
    user = User(
        id=uuid.uuid4(),
        email=f"inactive_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=None,
        role="BORROWER",
        status=UserStatus.INACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_active_user(db):
    """Create an active test user with password"""
    from app.core.security import get_password_hash
    user = User(
        id=uuid.uuid4(),
        email=f"active_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("ExistingPass123"),
        role="BORROWER",
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_set_password_success(client, test_inactive_user):
    """Test successful password setup"""
    # Create temp token
    temp_token = create_temp_token(
        data={"sub": str(test_inactive_user.id), "purpose": "password_setup"}
    )
    
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
    
    # Check response structure
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == str(test_inactive_user.id)
    assert data["role"] == "BORROWER"
    
    # Verify user is now active
    assert test_inactive_user.status == UserStatus.ACTIVE
    assert test_inactive_user.password_hash is not None

def test_set_password_invalid_token(client, test_inactive_user):
    """Test password setup with invalid token"""
    response = client.post(
        "/auth/set-password",
        json={
            "token": "invalid_token_12345",
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "token" in data["message"].lower()
        assert data["error_code"] in ["INVALID_TOKEN", "TOKEN_ERROR"]
    else:
        assert "detail" in data
        assert "token" in data["detail"].lower()

def test_set_password_expired_token(client, test_inactive_user):
    """Test password setup with expired token"""
    # Create token with immediate expiration (mock expired)
    from jose import jwt
    import os
    
    # Create an expired token by setting expiration in the past
    expired_payload = {
        "sub": str(test_inactive_user.id),
        "type": "temp",
        "exp": utc_now() - timedelta(minutes=1)  # Expired 1 minute ago
    }
    
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": expired_token,
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "expired" in data["message"].lower() or "invalid" in data["message"].lower()
    else:
        assert "detail" in data

def test_set_password_user_not_found(client):
    """Test password setup with non-existent user"""
    # Create token for non-existent user
    non_existent_id = uuid.uuid4()
    temp_token = create_temp_token(
        data={"sub": str(non_existent_id), "purpose": "password_setup"}
    )
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 404
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "not found" in data["message"].lower()
    else:
        assert "detail" in data
        assert "not found" in data["detail"].lower()

def test_set_password_already_active(client, test_active_user):
    """Test password setup for already active user"""
    # Create temp token for active user
    temp_token = create_temp_token(
        data={"sub": str(test_active_user.id), "purpose": "password_setup"}
    )
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "NewStrongP@ss123",
            "confirm_password": "NewStrongP@ss123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "active" in data["message"].lower()
        assert data["error_code"] == "USER_ALREADY_ACTIVE"
    else:
        assert "detail" in data
        assert "active" in data["detail"].lower()

def test_set_password_wrong_token_type(client, test_inactive_user):
    """Test password setup with wrong token type (access token instead of temp)"""
    # Create access token instead of temp token
    from app.core.security import create_access_token
    access_token = create_access_token(data={"sub": str(test_inactive_user.id)})
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": access_token,
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 401
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "token type" in data["message"].lower() or "invalid" in data["message"].lower()
    else:
        assert "detail" in data

def test_set_password_passwords_do_not_match(client, test_inactive_user):
    """Test password setup with mismatched passwords"""
    temp_token = create_temp_token(
        data={"sub": str(test_inactive_user.id), "purpose": "password_setup"}
    )
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "StrongP@ss123",
            "confirm_password": "DifferentPass456"
        }
    )
    
    assert response.status_code == 422  # Validation error from Pydantic
    data = response.json()
    
    # Pydantic validation error format
    if "detail" in data:
        assert "password" in str(data["detail"]).lower() or "match" in str(data["detail"]).lower()
    elif "errors" in data:
        assert any("password" in str(err).lower() for err in data["errors"])

def test_set_password_weak_password(client, test_inactive_user):
    """Test password setup with weak password"""
    temp_token = create_temp_token(
        data={"sub": str(test_inactive_user.id), "purpose": "password_setup"}
    )
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "weak",
            "confirm_password": "weak"
        }
    )
    
    assert response.status_code == 422  # Validation error
    data = response.json()
    
    if "detail" in data:
        assert "password" in str(data["detail"]).lower()
    elif "errors" in data:
        assert any("password" in str(err).lower() for err in data["errors"])

def test_set_password_no_token(client, test_inactive_user):
    """Test password setup without token"""
    response = client.post(
        "/auth/set-password",
        json={
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 422  # Validation error - missing token
    data = response.json()
    
    if "detail" in data:
        assert "token" in str(data["detail"]).lower()
    elif "errors" in data:
        assert any("token" in str(err).lower() for err in data["errors"])

def test_set_password_database_error(client, test_inactive_user, monkeypatch):
    """Test password setup with database error"""
    temp_token = create_temp_token(
        data={"sub": str(test_inactive_user.id), "purpose": "password_setup"}
    )
    
    # Mock the commit to raise an exception
    def mock_commit():
        raise Exception("Database connection failed")
    
    monkeypatch.setattr("sqlalchemy.orm.Session.commit", mock_commit)
    
    response = client.post(
        "/auth/set-password",
        json={
            "token": temp_token,
            "password": "StrongP@ss123",
            "confirm_password": "StrongP@ss123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "failed" in data["message"].lower()
        assert data["error_code"] == "PASSWORD_SETUP_ERROR"
    else:
        assert "detail" in data