# tests/test_loan.py

import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta

from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.loan import Loan, LoanStatus
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.core.security import create_access_token
from app.core.timezone import utc_now


#  FIXTURES 

@pytest.fixture
def test_borrower(db):
    user = User(
        id=uuid.uuid4(),
        email=f"borrower_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash="hashed_password",
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
        password_hash="hashed_password",
        role=UserRole.LENDER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543212",
        password_hash="hashed_password",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_loan(db, test_borrower, test_lender):
    loan = Loan(
        id=uuid.uuid4(),
        borrower_id=test_borrower.id,
        lender_id=test_lender.id,
        principal_amount=Decimal("100000"),
        tenure_months=12,
        interest_rate=Decimal("12.5"),
        emi_amount=Decimal("8884.91"),
        total_interest=Decimal("10661.88"),
        total_repayment=Decimal("110661.88"),
        status=LoanStatus.ACTIVE,
        disbursed_at=utc_now()
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@pytest.fixture
def test_repayment_schedules(db, test_loan):
    schedules = []
    for i in range(1, 4):
        schedule = RepaymentSchedule(
            loan_id=test_loan.id,
            installment_number=i,
            due_date=utc_now().date() + timedelta(days=30*i),
            amount_due=Decimal("8884.91"),
            principal_amount=Decimal("7884.91"),
            interest_amount=Decimal("1000.00"),
            amount_paid=Decimal("0"),
            status=RepaymentStatus.PENDING
        )
        db.add(schedule)
        schedules.append(schedule)
    db.commit()
    return schedules


@pytest.fixture
def borrower_auth_headers(test_borrower):
    token = create_access_token(data={"sub": str(test_borrower.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def lender_auth_headers(test_lender):
    token = create_access_token(data={"sub": str(test_lender.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin):
    token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}


#  TESTS 

def test_get_loans_as_borrower(client, test_loan, borrower_auth_headers):
    """Test borrower can view their loans"""
    response = client.get("/loans", headers=borrower_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["borrower_id"] == str(test_loan.borrower_id)


def test_get_loans_as_lender(client, test_loan, lender_auth_headers):
    """Test lender can view loans they funded"""
    response = client.get("/loans", headers=lender_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["lender_id"] == str(test_loan.lender_id)


def test_get_loans_as_admin(client, test_loan, admin_auth_headers):
    """Test admin can view all loans"""
    response = client.get("/loans", headers=admin_auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_loan_by_id(client, test_loan, borrower_auth_headers):
    """Test get specific loan details"""
    response = client.get(f"/loans/{test_loan.id}", headers=borrower_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_loan.id)
    assert "repayment_schedule" in data


def test_get_loan_not_found(client, borrower_auth_headers):
    """Test get non-existent loan"""
    response = client.get(f"/loans/{uuid.uuid4()}", headers=borrower_auth_headers)
    assert response.status_code == 404
    data = response.json()
    # Check for message in either 'message' or 'detail' field
    error_message = data.get("message", data.get("detail", ""))
    assert "not found" in error_message.lower()


def test_get_loan_unauthorized(client, test_loan, db):
    """Test unauthorized user cannot access loan"""
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        country_code="+91",
        national_number="9876543213",
        password_hash="hashed",
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(other_user)
    db.commit()
    
    token = create_access_token(data={"sub": str(other_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/loans/{test_loan.id}", headers=headers)
    assert response.status_code == 403
    data = response.json()
    # Check for message in either 'message' or 'detail' field
    error_message = data.get("message", data.get("detail", ""))
    assert "not authorized" in error_message.lower()


def test_get_repayment_schedule(client, test_loan, test_repayment_schedules, borrower_auth_headers):
    """Test get repayment schedule"""
    response = client.get(f"/loans/{test_loan.id}/schedule", headers=borrower_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "schedules" in data
    assert len(data["schedules"]) == 3
    assert "total_repayment" in data


def test_get_repayment_schedule_unauthorized(client, test_loan, db):
    """Test unauthorized user cannot view schedule"""
    other_user = User(
        id=uuid.uuid4(),
        email="other2@example.com",
        country_code="+91",
        national_number="9876543214",
        password_hash="hashed",
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(other_user)
    db.commit()
    
    token = create_access_token(data={"sub": str(other_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/loans/{test_loan.id}/schedule", headers=headers)
    assert response.status_code == 403
    data = response.json()
    error_message = data.get("message", data.get("detail", ""))
    assert "not authorized" in error_message.lower()