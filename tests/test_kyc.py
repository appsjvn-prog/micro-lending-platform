import pytest
import uuid
from datetime import date
from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.kyc import KYC, KYCStatus, KYCDocument, KYCDocumentType
from app.core.security import get_password_hash, create_access_token


# ============== FIXTURES ==============

@pytest.fixture
def test_user(db):
    """Create a test borrower user"""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
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
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_user_profile(db, test_user):
    """Create a user profile for the test user"""
    profile = UserProfile(
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        dob=date(1990, 1, 1),
        gender="MALE",
        email=test_user.email,
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


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


@pytest.fixture
def test_kyc(db, test_user):
    """Create a KYC record for testing"""
    kyc = KYC(
        user_id=test_user.id,
        status=KYCStatus.PENDING
    )
    db.add(kyc)
    db.commit()
    db.refresh(kyc)
    return kyc


@pytest.fixture
def test_kyc_document(db, test_kyc):
    """Create a KYC document for testing"""
    doc = KYCDocument(
        request_id=test_kyc.id,
        doc_type=KYCDocumentType.PAN,
        file_url="https://example.com/pan.pdf"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ============== TEST SUBMIT KYC ==============

def test_submit_kyc_success(client, test_user_profile, auth_headers):
    """Test successful KYC submission"""
    response = client.post("/kyc/submit", headers=auth_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    assert "created_at" in data


def test_submit_kyc_duplicate(client, test_user_profile, auth_headers):
    """Test submitting duplicate KYC should fail"""
    # First submission
    response1 = client.post("/kyc/submit", headers=auth_headers)
    assert response1.status_code == 201
    
    # Second submission
    response2 = client.post("/kyc/submit", headers=auth_headers)
    
    assert response2.status_code == 400
    data = response2.json()
    assert "already" in str(data).lower()


def test_submit_kyc_unauthorized(client):
    """Test submitting KYC without authentication"""
    response = client.post("/kyc/submit")
    assert response.status_code == 401


# ============== TEST UPLOAD DOCUMENTS ==============

def test_upload_document_success(client, test_kyc, auth_headers):
    """Test successful document upload"""
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan.pdf"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["doc_type"] == "PAN"


def test_upload_document_without_kyc(client, auth_headers):
    """Test uploading document without submitting KYC first"""
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan.pdf"
        }
    )

    assert response.status_code == 400
    assert response.json() is not None


def test_upload_duplicate_document(client, test_kyc, auth_headers):
    """Test uploading duplicate document type"""
    # First upload
    response1 = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan1.pdf"
        }
    )
    assert response1.status_code == 201
    
    # Second upload same type
    response2 = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan2.pdf"
        }
    )
    
    assert response2.status_code == 400
    data = response2.json()
    assert "already uploaded" in str(data).lower()


def test_upload_document_after_verification(client, test_kyc, auth_headers, admin_auth_headers):
    """Test uploading document after KYC is verified (should fail)"""
    # Upload document
    client.post("/kyc/documents", headers=auth_headers, json={
        "doc_type": "PAN",
        "file_url": "https://example.com/pan.pdf"
    })
    
    # Admin verifies KYC
    client.patch(f"/kyc/{test_kyc.id}/review", headers=admin_auth_headers, json={
        "status": "VERIFIED"
    })
    
    # Try to upload another document
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "AADHAAR",
            "file_url": "https://example.com/aadhaar.pdf"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already verified" in str(data).lower()


# ============== TEST GET KYC ==============

def test_get_my_kyc(client, test_kyc, auth_headers):
    """Test getting own KYC status"""
    response = client.get("/kyc", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_kyc.id)
    assert data["status"] == "PENDING"


def test_get_kyc_not_found(client, auth_headers):
    """Test getting KYC when none exists"""
    response = client.get("/kyc", headers=auth_headers)
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


def test_admin_get_all_kyc(client, test_kyc, admin_auth_headers):
    """Test admin getting all KYC submissions"""
    response = client.get("/kyc", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == "PENDING"


def test_admin_get_kyc_by_id(client, test_kyc, admin_auth_headers):
    """Test admin getting specific KYC by ID"""
    response = client.get(f"/kyc?kyc_id={test_kyc.id}", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_kyc.id)


# ============== TEST REVIEW KYC ==============

def test_admin_verify_kyc(client, test_kyc, test_kyc_document, admin_auth_headers):
    """Test admin verifying KYC"""
    response = client.patch(
        f"/kyc/{test_kyc.id}/review",
        headers=admin_auth_headers,
        json={
            "status": "VERIFIED"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["overall_updated"] == True
    assert data["overall_status"] == "VERIFIED"


def test_admin_reject_kyc(client, test_kyc, admin_auth_headers):
    """Test admin rejecting KYC"""
    response = client.patch(
        f"/kyc/{test_kyc.id}/review",
        headers=admin_auth_headers,
        json={
            "status": "REJECTED",
            "rejection_reason": "Invalid documents"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["overall_updated"] == True
    assert data["overall_status"] == "REJECTED"


def test_admin_review_document(client, test_kyc, test_kyc_document, admin_auth_headers):
    """Test admin reviewing individual document"""
    response = client.patch(
        f"/kyc/{test_kyc.id}/review",
        headers=admin_auth_headers,
        json={
            "documents": [
                {
                    "document_id": str(test_kyc_document.id),
                    "is_verified": True
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["updated_documents"]) == 1
    assert data["updated_documents"][0]["is_verified"] == True


def test_non_admin_cannot_review(client, test_kyc, auth_headers):
    """Test non-admin cannot review KYC"""
    response = client.patch(
        f"/kyc/{test_kyc.id}/review",
        headers=auth_headers,
        json={
            "status": "VERIFIED"
        }
    )
    
    assert response.status_code == 403


def test_review_nonexistent_kyc(client, admin_auth_headers):
    """Test reviewing non-existent KYC"""
    fake_id = uuid.uuid4()
    response = client.patch(
        f"/kyc/{fake_id}/review",
        headers=admin_auth_headers,
        json={
            "status": "VERIFIED"
        }
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


# ============== TEST KYC STATS ==============

def test_get_kyc_stats(client, test_kyc, admin_auth_headers):
    """Test getting KYC statistics (admin only)"""
    response = client.get("/kyc/stats", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_submissions" in data
    assert "pending" in data
    assert "verified" in data
    assert "rejected" in data


def test_non_admin_cannot_get_stats(client, auth_headers):
    """Test non-admin cannot get KYC stats"""
    response = client.get("/kyc/stats", headers=auth_headers)
    
    assert response.status_code == 403


# ============== TEST RE-UPLOAD REJECTED DOCUMENT ==============

def test_reupload_rejected_document(client, test_kyc, auth_headers, admin_auth_headers):
    """Test re-uploading a rejected document"""
    # Upload document
    upload_response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan.pdf"
        }
    )
    doc_id = upload_response.json()["id"]
    
    # Admin rejects the document
    client.patch(
        f"/kyc/{test_kyc.id}/review",
        headers=admin_auth_headers,
        json={
            "documents": [
                {
                    "document_id": doc_id,
                    "is_verified": False,
                    "rejection_reason": "Document unclear"
                }
            ]
        }
    )
    
    # Re-upload same document type
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN",
            "file_url": "https://example.com/pan_new.pdf"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["doc_type"] == "PAN"


# ============== TEST EDGE CASES ==============

def test_upload_document_invalid_type(client, test_kyc, auth_headers):
    """Test uploading document with invalid type"""
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "INVALID",
            "file_url": "https://example.com/doc.pdf"
        }
    )
    
    assert response.status_code == 422


def test_upload_document_missing_url(client, test_kyc, auth_headers):
    """Test uploading document without URL"""
    response = client.post(
        "/kyc/documents",
        headers=auth_headers,
        json={
            "doc_type": "PAN"
        }
    )
    
    assert response.status_code == 422


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])