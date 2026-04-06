from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.user import User
from app.models.borrower_profile import BorrowerProfile, EmploymentType
from app.models.loan import Loan, LoanStatus
from app.models.kyc import KYC, KYCStatus
from app.models.repayment_schedule import RepaymentSchedule, RepaymentStatus
from app.core.timezone import utc_now


class RiskScoreCalculator:
    def __init__(self, db: Session):
        self.db = db

    def calculate_risk_score(self, user_id: str, for_lender: bool = False) -> dict:
        """Calculate risk score for a borrower based on their profile and loan history"""
        
        profile = self.db.query(BorrowerProfile).filter(
            BorrowerProfile.user_id == user_id
        ).first()

        if not profile:
            return {"error": "Borrower profile not found"}
        
        score = 50  # Start neutral

        # ========== 1. INCOME FACTOR (0-25 points) ==========
        income_score = 0  # ✅ Initialize
        if profile.monthly_income >= 100000:
            income_score = 25
        elif profile.monthly_income >= 50000:
            income_score = 15
        elif profile.monthly_income >= 25000:
            income_score = 10
        elif profile.monthly_income >= 15000:
            income_score = 5
        else:
            income_score = 0
        
        score += income_score

        # ========== 2. EMPLOYMENT TYPE FACTOR (0-20 points) ==========
        employment_scores = {
            EmploymentType.SALARIED: 20,
            EmploymentType.SELF_EMPLOYED: 15,
            EmploymentType.BUSINESS: 15,
            EmploymentType.STUDENT: 5,
            EmploymentType.UNEMPLOYED: 0
        }
        score += employment_scores.get(profile.employment_type, 10)

        # ========== 3. JOB TENURE FACTOR (0-10 points) ==========
        if profile.current_job_tenure_months:
            if profile.current_job_tenure_months >= 24:
                score += 10
            elif profile.current_job_tenure_months >= 12:
                score += 7
            elif profile.current_job_tenure_months >= 6:
                score += 4
            elif profile.current_job_tenure_months >= 3:
                score += 2

        # ========== 4. KYC VERIFICATION FACTOR (0-15 points) ==========
        kyc = self.db.query(KYC).filter(KYC.user_id == user_id).first()
        if kyc:
            if kyc.status == KYCStatus.VERIFIED:
                score += 15
            elif kyc.status == KYCStatus.PENDING:
                score += 5

        # ========== 5. DEBT-TO-INCOME RATIO PENALTY (0 to -25 points) ==========
        active_loans = self.db.query(Loan).filter(
            Loan.borrower_id == user_id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.DISBURSED])
        ).all()
        
        total_monthly_emi = sum(float(loan.emi_amount or 0) for loan in active_loans)
        monthly_income = float(profile.monthly_income)
        
        if monthly_income > 0:
            dti_ratio = (total_monthly_emi / monthly_income) * 100
            if dti_ratio >= 60:
                score -= 25
            elif dti_ratio >= 40:
                score -= 15
            elif dti_ratio >= 25:
                score -= 8
            elif dti_ratio >= 10:
                score -= 3

        # ========== 6. REPAYMENT HISTORY SCORE (0-25 points) ==========
        repayment_score = self.calculate_repayment_history_score(user_id)
        score += repayment_score

        # Cap score between 0 and 100
        score = max(0, min(100, score))

        # Determine risk level
        if score >= 70:
            risk_level = "LOW"
        elif score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        result = {
            "user_id": user_id,
            "score": round(score, 2),
            "risk_level": risk_level,
        }
        
        if not for_lender:
            result["breakdown"] = {
                "income": income_score,  # ✅ Use the variable directly
                "employment_type": employment_scores.get(profile.employment_type, 10),
                "job_tenure": min(10, score),
                "kyc_verified": 15 if (kyc and kyc.status == KYCStatus.VERIFIED) else (5 if kyc else 0),
                "debt_to_income_penalty": -min(25, abs(score - 50)),
                "repayment_history": repayment_score
            }
        
        return result

    def calculate_repayment_history_score(self, user_id: str) -> int:
        """Calculate score based on repayment behavior (0-25 points)"""

        schedules = self.db.query(RepaymentSchedule).join(
            Loan, RepaymentSchedule.loan_id == Loan.id
        ).filter(
            Loan.borrower_id == user_id
        ).all()

        if not schedules:
            return 0

        total_paid = sum(1 for s in schedules if s.status in [RepaymentStatus.PAID, RepaymentStatus.PAID_LATE])
        total_paid_on_time = sum(1 for s in schedules if s.status == RepaymentStatus.PAID)
        total_late = sum(1 for s in schedules if s.status == RepaymentStatus.PAID_LATE)
        total_overdue = sum(1 for s in schedules if s.status == RepaymentStatus.OVERDUE)

        if total_paid == 0:
            return -10

        on_time_rate = (total_paid_on_time / total_paid) * 100

        late_penalty = 0
        if total_late > 0:
            late_penalty = min(15, total_late * 3)

        overdue_penalty = 0
        if total_overdue > 0:
            overdue_penalty = min(25, total_overdue * 5)

        if on_time_rate >= 95:
            base_score = 25
        elif on_time_rate >= 90:
            base_score = 20
        elif on_time_rate >= 80:
            base_score = 15
        elif on_time_rate >= 70:
            base_score = 10
        elif on_time_rate >= 50:
            base_score = 5
        else:
            base_score = 0

        final_score = base_score - late_penalty - overdue_penalty

        return max(0, min(25, final_score))