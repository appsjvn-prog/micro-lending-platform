import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.borrower_profile import BorrowerProfile, EmploymentType
from app.models.lender_profile import LenderProfile, RiskAppetite, LenderStatus
from app.models.bank_account import BankAccount, AccountType
from app.models.loan import Loan, LoanStatus
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.models.loan_application import LoanApplication, LoanApplicationStatus
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.models.transaction import Transaction, TransactionType
from app.core.security import get_password_hash, create_access_token
from app.core.timezone import utc_now


# ============== FIXTURES ==============

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
        dob=date(1990, 1, 1),
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
def test_borrower_account(db, test_borrower):
    account = BankAccount(
        user_id=test_borrower.id,
        bank_name="SBI",
        account_holder_name="Test Borrower",
        account_type=AccountType.SAVINGS,
        account_number="123456789012",
        ifsc_code="SBIN0001234",
        is_primary=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_lender_account(db, test_lender):
    account = BankAccount(
        user_id=test_lender.id,
        bank_name="HDFC",
        account_holder_name="Test Lender",
        account_type=AccountType.SAVINGS,
        account_number="098765432109",
        ifsc_code="HDFC0005678",
        is_primary=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_loan_offer(db, test_lender):
    offer = LoanOffer(
        lender_id=test_lender.id,
        offer_name="Personal Loan",
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
def test_loan(db, test_borrower, test_lender, test_loan_offer):
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
    """Create realistic repayment schedules"""
    schedules = []
    emi_amount = Decimal("8884.91")  # EMI amount
    principal_per_month = Decimal("7884.91")
    interest_per_month = Decimal("1000.00")
    
    for i in range(1, 4):
        schedule = RepaymentSchedule(
            loan_id=test_loan.id,
            installment_number=i,
            due_date=utc_now().date() + timedelta(days=30*i),
            amount_due=emi_amount,
            principal_amount=principal_per_month,
            interest_amount=interest_per_month,
            amount_paid=Decimal("0"),
            status=RepaymentStatus.PENDING
        )
        db.add(schedule)
        schedules.append(schedule)
    db.commit()
    return schedules

@pytest.fixture
def borrower_auth_headers(test_borrower):
    access_token = create_access_token(data={"sub": str(test_borrower.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def lender_auth_headers(test_lender):
    access_token = create_access_token(data={"sub": str(test_lender.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_repayment_data(test_loan):
    return {
        "loan_id": str(test_loan.id),
        "amount": 5000.00
    }


# ============== TEST FLEXIBLE REPAYMENT ==============

def test_flexible_repayment_success(client, test_loan, test_repayment_schedules, 
                                     test_borrower_account, test_lender_account, 
                                     borrower_auth_headers):
    """Test successful flexible repayment"""
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "amount": 5000.00
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] == True
    assert data["payment_amount"] == 5000.00
    assert data["is_loan_fully_paid"] == False
    assert "transaction_id" in data


def test_flexible_repayment_full_payment(client, test_loan, test_repayment_schedules,
                                          test_borrower_account, test_lender_account,
                                          borrower_auth_headers):
    """Test full repayment of loan"""
    total = sum(s.amount_due for s in test_repayment_schedules)
    
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": float(total)
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] == True
    assert data["is_loan_fully_paid"] == True
    assert data["loan_status"] == "CLOSED"


def test_flexible_repayment_loan_not_found(client, borrower_auth_headers):
    """Test repayment for non-existent loan"""
    fake_id = uuid.uuid4()
    response = client.post(
        f"/transactions/loans/{fake_id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(uuid.uuid4()),
            "amount": 5000.00
        }
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


def test_flexible_repayment_unauthorized(client, test_loan, lender_auth_headers):
    """Test lender cannot make repayment (only borrower)"""
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=lender_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 5000.00
        }
    )
    
    assert response.status_code == 403
    data = response.json()
    assert "authorized" in str(data).lower()


def test_flexible_repayment_overpayment(client, test_loan, test_repayment_schedules,
                                         test_borrower_account, test_lender_account,
                                         borrower_auth_headers):
    """Test overpayment should fail"""
    total = sum(s.amount_due for s in test_repayment_schedules)
    
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": float(total) + 1000
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "exceeds" in str(data).lower() or "overpayment" in str(data).lower()


def test_flexible_repayment_zero_amount(client, test_loan, borrower_auth_headers):
    """Test repayment with zero amount should fail"""
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 0
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "greater than" in str(data).lower()


def test_flexible_repayment_negative_amount(client, test_loan, borrower_auth_headers):
    """Test repayment with negative amount should fail"""
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": -100
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "greater than" in str(data).lower()

# ============== TEST GET TRANSACTIONS ==============

def test_get_loan_transactions(client, test_loan, test_repayment_schedules,
                                test_borrower_account, test_lender_account,
                                borrower_auth_headers, db):
    """Test getting transactions for a loan"""
    from app.models.transaction import Transaction
    
    # Make a payment first (this creates a transaction)
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 5000.00
        }
    )
    assert response.status_code == 201
    
    # Now get transactions
    response = client.get(f"/transactions/loan/{test_loan.id}", headers=borrower_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["type"] == "REPAYMENT"

def test_get_loan_transactions_unauthorized(client, test_loan, lender_auth_headers):
    """Test lender cannot view borrower's transactions? Actually lender should be able to"""
    response = client.get(f"/transactions/loan/{test_loan.id}", headers=lender_auth_headers)
    
    # Lender should be able to view transactions for their loan
    assert response.status_code == 200


def test_get_loan_transactions_not_found(client, borrower_auth_headers):
    """Test getting transactions for non-existent loan"""
    response = client.get(f"/transactions/loan/{uuid.uuid4()}", headers=borrower_auth_headers)
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


def test_get_my_transactions(client, test_loan, test_repayment_schedules,
                              test_borrower_account, test_lender_account,
                              borrower_auth_headers):
    """Test getting user's own transactions"""
    # Make a payment first
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 5000.00
        }
    )
    assert response.status_code == 201
    
    # Get user transactions
    response = client.get("/transactions/user", headers=borrower_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_get_my_transactions_no_account(client, test_borrower, db):
    """Test getting transactions when user has no bank account"""
    # Create a borrower without bank account
    borrower_no_account = User(
        id=uuid.uuid4(),
        email="no_account@example.com",
        country_code="+91",
        national_number="9876543215",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(borrower_no_account)
    db.commit()
    
    token = create_access_token(data={"sub": str(borrower_no_account.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/transactions/user", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data == []


# ============== TEST UNAUTHORIZED ACCESS ==============

def test_unauthorized_access_no_token(client):
    fake_id = uuid.uuid4()
    """Test accessing transactions without authentication"""
    response = client.post(f"/transactions/loans/{fake_id}", json={})
    assert response.status_code == 401
    
    response = client.get("/transactions/user")
    assert response.status_code == 401


# ============== TEST PARTIAL PAYMENT SCENARIOS ==============

def test_partial_payment_multiple_installments(client, test_loan, test_repayment_schedules,
                                                test_borrower_account, test_lender_account,
                                                borrower_auth_headers):
    """Test partial payment that covers part of first and second installment"""
    # First installment amount is 8884.91
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 10000.00
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 2
    assert data["allocations"][0]["type"] == "FULL"
    assert data["allocations"][1]["type"] == "PARTIAL"
    assert data["is_loan_fully_paid"] == False


def test_exact_emi_payment(client, test_loan, test_repayment_schedules,
                           test_borrower_account, test_lender_account,
                           borrower_auth_headers):
    """Test exact EMI payment"""
    response = client.post(
        f"/transactions/loans/{test_loan.id}",
        headers=borrower_auth_headers,
        json={
            "loan_id": str(test_loan.id),
            "amount": 8884.91
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["type"] == "FULL"
    assert data["allocations"][0]["installment_number"] == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])