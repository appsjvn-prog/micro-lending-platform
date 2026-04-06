import pytest
import uuid
from datetime import datetime, date, timedelta
from app.models.user import User, UserStatus
from app.models.user_profile import UserProfile
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=get_password_hash("TestPass123"),
        role="BORROWER",
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("AdminPass123"),
        role="ADMIN",
        status=UserStatus.ACTIVE
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

@pytest.fixture
def auth_headers(test_user):
    """Get auth headers for test user"""
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def admin_auth_headers(test_admin):
    """Get auth headers for admin user"""
    access_token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {access_token}"}

def test_create_user_profile_success(client, db, test_user, auth_headers):
    """Test successful profile creation"""
    response = client.post(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": "john@example.com",
            "mobile": {
                "country_code": "+91",
                "national_number": "9876543210"
            }
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "created_at" in data
    assert "User profile created successfully" in data["message"]
    
    # Verify profile in DB
    profile = db.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    assert profile is not None
    assert profile.first_name == "John"
    assert profile.last_name == "Doe"

def test_create_profile_phone_mismatch(client, test_user, auth_headers):
    """Test profile creation with mismatched phone"""
    response = client.post(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": "john@example.com",
            "mobile": {
                "country_code": "+91",
                "national_number": "9999999999"  # Different phone
            }
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    # Check for the error code
    if "error_code" in data:
        assert data["error_code"] in ["PROFILE_PHONE_MISMATCH", "PROFILE_PHONE_MISMATCH_EXCEPTION", "VALIDATION_ERROR"]
    elif "success" in data:
        assert data["success"] == False
        assert "phone" in data["message"].lower() or "match" in data["message"].lower()
    else:
        assert "detail" in data
        assert "phone" in data["detail"].lower()

def test_create_duplicate_profile(client, db, test_user, auth_headers):
    """Test creating duplicate profile"""
    # First profile
    response1 = client.post(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": "john@example.com",
            "mobile": {
                "country_code": "+91",
                "national_number": "9876543210"
            }
        }
    )
    assert response1.status_code == 201
    
    # Second profile (should fail)
    response2 = client.post(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1992-01-01",
            "gender": "FEMALE",
            "email": "jane@example.com",
            "mobile": {
                "country_code": "+91",
                "national_number": "9876543210"
            }
        }
    )
    
    assert response2.status_code == 400
    data = response2.json()
    
    if "error_code" in data:
        assert data["error_code"] in ["PROFILE_ALREADY_EXISTS", "PROFILE_ALREADY_EXISTS_EXCEPTION"]
    elif "success" in data:
        assert data["success"] == False
        assert "already exists" in data["message"].lower()
    else:
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

def test_get_my_profile_success(client, db, test_user, auth_headers):
    """Test getting own profile"""
    # Create profile first
    profile = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    
    # Get profile
    response = client.get("/user/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    # For regular user, it returns a single object, not a list
    assert isinstance(data, dict)
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "john@example.com"

def test_get_my_profile_not_found(client, test_user, auth_headers):
    """Test getting profile when it doesn't exist"""
    response = client.get("/user/profile", headers=auth_headers)
    
    assert response.status_code == 404
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "not found" in data["message"].lower()
    else:
        assert "detail" in data
        assert "not found" in data["detail"].lower()

def test_get_all_profiles_as_admin(client, db, test_user, test_admin, admin_auth_headers):
    """Test admin getting all profiles"""
    # Create profiles
    profile1 = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile1)
    
    user2 = User(
        id=uuid.uuid4(),
        email="user2@example.com",
        country_code="+91",
        national_number="9876543212",
        password_hash=get_password_hash("TestPass123"),
        role="BORROWER",
        status=UserStatus.ACTIVE
    )
    db.add(user2)
    
    profile2 = UserProfile(
        user_id=user2.id,
        first_name="Jane",
        last_name="Smith",
        dob=date(1992, 1, 1),
        gender="FEMALE",
        email="jane@example.com",
        country_code="+91",
        national_number="9876543212"
    )
    db.add(profile2)
    db.commit()
    
    # Admin gets all profiles - returns a list
    response = client.get("/user/profile", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Check both profiles exist
    names = [p["first_name"] for p in data]
    assert "John" in names
    assert "Jane" in names

def test_update_profile_success(client, db, test_user, auth_headers):
    """Test updating profile"""
    # Create profile first
    profile = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    
    # Update profile
    response = client.put(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "Jonathan",
            "last_name": "Smith",
            "email": "jonathan@example.com"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jonathan"
    assert data["last_name"] == "Smith"
    assert data["email"] == "jonathan@example.com"

def test_update_profile_not_found(client, test_user, auth_headers):
    """Test updating non-existent profile"""
    response = client.put(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "Jonathan"
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

def test_update_profile_with_alternate_mobile(client, db, test_user, auth_headers):
    """Test updating profile with alternate mobile"""
    # Create profile
    profile = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    
    # Update with alternate mobile
    response = client.put(
        "/user/profile",
        headers=auth_headers,
        json={
            "alternate_mobile": {
                "country_code": "+91",
                "national_number": "8888888888"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check the response - alternate mobile fields might be nested or flattened
    if "alternate_mobile" in data:
        assert data["alternate_mobile"]["country_code"] == "+91"
        assert data["alternate_mobile"]["national_number"] == "8888888888"
    elif "alternate_country_code" in data:
        assert data["alternate_country_code"] == "+91"
        assert data["alternate_national_number"] == "8888888888"
    else:
        # If fields are not in response, at least verify the update worked
        db.refresh(profile)
        assert profile.alternate_country_code == "+91"
        assert profile.alternate_national_number == "8888888888"

def test_delete_profile_success(client, db, test_user, auth_headers):
    """Test deleting profile"""
    # Create profile
    profile = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    
    # Delete profile
    response = client.delete("/user/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "deleted" in data["message"].lower()
    
    # Verify profile is deleted
    deleted_profile = db.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    assert deleted_profile is None

def test_delete_profile_not_found(client, test_user, auth_headers):
    """Test deleting non-existent profile"""
    response = client.delete("/user/profile", headers=auth_headers)
    
    assert response.status_code == 404
    data = response.json()
    
    if "success" in data:
        assert data["success"] == False
        assert "not found" in data["message"].lower()
    else:
        assert "detail" in data
        assert "not found" in data["detail"].lower()

def test_get_own_profile_through_profiles_endpoint(client, db, test_user, auth_headers):
    """Test regular user getting their profile through profiles endpoint"""
    # Create profile
    profile = UserProfile(
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
        gender="MALE",
        email="john@example.com",
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    
    # ✅ FIXED: Use the correct endpoint
    response = client.get("/user/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    # ✅ FIXED: For regular user, it returns a single object, not a list
    assert isinstance(data, dict)
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "john@example.com"

def test_create_profile_with_alternate_mobile(client, db, test_user, auth_headers):
    """Test creating profile with alternate mobile"""
    response = client.post(
        "/user/profile",
        headers=auth_headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": "john@example.com",
            "mobile": {
                "country_code": "+91",
                "national_number": "9876543210"
            },
            "alternate_mobile": {
                "country_code": "+91",
                "national_number": "8888888888"
            }
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    
    # Verify alternate mobile in DB
    profile = db.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    assert profile.alternate_country_code == "+91"
    assert profile.alternate_national_number == "8888888888"