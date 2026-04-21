import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.borrower_profile import BorrowerProfile, EmploymentType
from app.models.lender_profile import LenderProfile, RiskAppetite, LenderStatus
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.models.loan_application import LoanApplication, LoanApplicationStatus
from app.models.loan import Loan
from app.core.security import get_password_hash, create_access_token
from app.core.timezone import utc_now


#  FIXTURES 

@pytest.fixture
def test_borrower(db):
    user = User(
        id=uuid.uuid4(),
        email=f"borrower_{uuid.uuid4().hex[:8]}@example.com",
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
def test_lender(db):
    user = User(
        id=uuid.uuid4(),
        email=f"lender_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.LENDER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_profile(db, test_borrower):
    profile = UserProfile(
        user_id=test_borrower.id,
        first_name="Test",
        last_name="Borrower",
        dob=datetime.now().date() - relativedelta(years=30),
        gender="MALE",
        email=test_borrower.email,
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def test_borrower_profile(db, test_borrower):
    profile = BorrowerProfile(
        user_id=test_borrower.id,
        employment_type=EmploymentType.SALARIED,
        monthly_income=Decimal("50000"),
        employer_name="Tech Corp",
        current_job_tenure_months=24,
        total_work_experience_years=5,
        is_profile_complete=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def test_lender_profile(db, test_lender):
    profile = LenderProfile(
        user_id=test_lender.id,
        profile_name="Test Lender",
        business_type="INDIVIDUAL",
        risk_appetite=RiskAppetite.MEDIUM,
        status=LenderStatus.ACTIVE,
        is_verified=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def test_loan_offer(db, test_lender):
    offer = LoanOffer(
        lender_id=test_lender.id,
        offer_name="Personal Loan Offer",
        description="Competitive interest rates",
        min_amount=Decimal("10000"),
        max_amount=Decimal("500000"),
        min_tenure_months=6,
        max_tenure_months=36,
        interest_rate=Decimal("12.5"),
        status=LoanOfferStatus.ACTIVE,
        expires_at=utc_now() + timedelta(days=30)
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@pytest.fixture
def borrower_auth_headers(test_borrower):
    access_token = create_access_token(data={"sub": str(test_borrower.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def lender_auth_headers(test_lender):
    access_token = create_access_token(data={"sub": str(test_lender.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_application_data(test_loan_offer):
    return {
        "loan_offer_id": str(test_loan_offer.id),
        "requested_amount": 50000.00,
        "requested_tenure": 12,
        "purpose": "Home renovation",
        "notes": "Need to renovate kitchen"
    }


#  TEST CREATE 

def test_create_application_success(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDING"


def test_create_application_duplicate(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    assert response.status_code == 400


def test_create_application_invalid_amount(client, test_user_profile, test_borrower_profile, borrower_auth_headers, test_loan_offer):
    response = client.post(
        "/loan-applications",
        headers=borrower_auth_headers,
        json={
            "loan_offer_id": str(test_loan_offer.id),
            "requested_amount": 1000.00,
            "requested_tenure": 12
        }
    )
    assert response.status_code == 400


def test_create_application_offer_not_found(client, test_user_profile, test_borrower_profile, borrower_auth_headers):
    response = client.post(
        "/loan-applications",
        headers=borrower_auth_headers,
        json={
            "loan_offer_id": str(uuid.uuid4()),
            "requested_amount": 50000.00,
            "requested_tenure": 12
        }
    )
    assert response.status_code == 404


def test_create_application_as_lender(client, lender_auth_headers, sample_application_data):
    response = client.post("/loan-applications", headers=lender_auth_headers, json=sample_application_data)
    assert response.status_code == 403


#  TEST GET 

def test_get_borrower_applications(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    response = client.get("/loan-applications", headers=borrower_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_lender_applications(client, test_user_profile, test_borrower_profile, borrower_auth_headers, lender_auth_headers, sample_application_data):
    client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    response = client.get("/loan-applications", headers=lender_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


#  TEST UPDATE 

def test_update_application_success(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    response = client.put(
        f"/loan-applications/{app_id}",
        headers=borrower_auth_headers,
        json={"requested_amount": 60000.00}
    )
    assert response.status_code == 200


def test_update_application_not_found(client, borrower_auth_headers):
    response = client.put(f"/loan-applications/{uuid.uuid4()}", headers=borrower_auth_headers, json={"requested_amount": 60000.00})
    assert response.status_code == 404


#  TEST REVIEW 

def test_review_application_accept(client, test_user_profile, test_borrower_profile, borrower_auth_headers, lender_auth_headers, sample_application_data, db):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    response = client.post(
        f"/loan-applications/{app_id}/review",
        headers=lender_auth_headers,
        json={"status": "ACCEPTED", "lender_notes": "Approved"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    
    loan = db.query(Loan).filter(Loan.loan_application_id == app_id).first()
    assert loan is not None


def test_review_application_reject(client, test_user_profile, test_borrower_profile, borrower_auth_headers, lender_auth_headers, sample_application_data, db):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    response = client.post(
        f"/loan-applications/{app_id}/review",
        headers=lender_auth_headers,
        json={"status": "REJECTED", "lender_notes": "Not approved"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    
    loan = db.query(Loan).filter(Loan.loan_application_id == app_id).first()
    assert loan is None


def test_review_application_unauthorized(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    response = client.post(
        f"/loan-applications/{app_id}/review",
        headers=borrower_auth_headers,
        json={"status": "ACCEPTED"}
    )
    assert response.status_code == 403


def test_review_application_not_found(client, lender_auth_headers):
    response = client.post(
        f"/loan-applications/{uuid.uuid4()}/review",
        headers=lender_auth_headers,
        json={"status": "ACCEPTED"}
    )
    assert response.status_code == 404


#  TEST CANCEL 

def test_cancel_application_success(client, test_user_profile, test_borrower_profile, borrower_auth_headers, sample_application_data):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    response = client.post(f"/loan-applications/{app_id}/cancel", headers=borrower_auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancel_application_not_found(client, borrower_auth_headers):
    response = client.post(f"/loan-applications/{uuid.uuid4()}/cancel", headers=borrower_auth_headers)
    assert response.status_code == 404


def test_cancel_application_already_reviewed(client, test_user_profile, test_borrower_profile, borrower_auth_headers, lender_auth_headers, sample_application_data):
    create_response = client.post("/loan-applications", headers=borrower_auth_headers, json=sample_application_data)
    app_id = create_response.json()["id"]
    
    client.post(f"/loan-applications/{app_id}/review", headers=lender_auth_headers, json={"status": "ACCEPTED"})
    response = client.post(f"/loan-applications/{app_id}/cancel", headers=borrower_auth_headers)
    assert response.status_code in [400, 403]


#  TEST UNAUTHORIZED 

def test_unauthorized_access_no_token(client):
    response_post = client.post("/loan-applications", json={})
    assert response_post.status_code == 401