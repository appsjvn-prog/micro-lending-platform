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
        
        # Start neutral
        income_score = 0
        employment_score = 0
        tenure_score = 0
        kyc_score = 0
        dti_penalty = 0
        repayment_score = 0
          

        # 1. INCOME FACTOR (0-25 points) 
        
        if profile.monthly_income >= 200000:
            income_score = 20
        elif profile.monthly_income >= 100000:
            income_score = 15
        elif profile.monthly_income >= 60000:
            income_score = 10
        elif profile.monthly_income >= 30000:
            income_score = 5
        elif profile.monthly_income >= 15000:
            income_score = 2
        else:
            income_score = 0

        # 2. EMPLOYMENT TYPE FACTOR (0-20 points) 
        employment_scores = {
            EmploymentType.SALARIED: 15,
            EmploymentType.SELF_EMPLOYED: 10,
            EmploymentType.BUSINESS: 10,
            EmploymentType.STUDENT: 3,
            EmploymentType.UNEMPLOYED: 0
        }
        employment_score = employment_scores.get(profile.employment_type,3)

        #3. JOB TENURE FACTOR (0-10 points)
        if profile.current_job_tenure_months:
            if profile.current_job_tenure_months >= 36:
                tenure_score = 10
            elif profile.current_job_tenure_months >= 24:
                tenure_score = 7
            elif profile.current_job_tenure_months >= 12:
                tenure_score = 5
            elif profile.current_job_tenure_months >= 6:
                tenure_score = 3
            elif profile.current_job_tenure_months >=3:
                tenure_score =1


        # 4. KYC VERIFICATION FACTOR 
        kyc = self.db.query(KYC).filter(KYC.user_id == user_id).first()
        if kyc:
            if kyc.status == KYCStatus.VERIFIED:
                kyc_score = 10
            elif kyc.status == KYCStatus.PENDING:
                kyc_score = 3

        #  5. DEBT-TO-INCOME RATIO PENALTY (0 to -25 points) 
        active_loans = self.db.query(Loan).filter(
            Loan.borrower_id == user_id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.DISBURSED])
        ).all()
        
        total_monthly_emi = sum(
            loan.emi_amount if loan.emi_amount else Decimal('0') 
        for loan in active_loans
         )       
        monthly_income = profile.monthly_income

        dti_penalty = 0
        if monthly_income > 0:
            dti_ratio = (total_monthly_emi / monthly_income) * Decimal('100')
            if dti_ratio >= 50:
                dti_penalty = -30
            elif dti_ratio >= 40:
                dti_penalty = -20
            elif dti_ratio >= 30:
                dti_penalty = -12
            elif dti_ratio >= 20:
                dti_penalty = -6
            elif dti_ratio >= 10:
                dti_penalty = -2

        # 6. REPAYMENT HISTORY SCORE (0-25 points)
        repayment_score = self.calculate_repayment_history_score(user_id)

        score = income_score + employment_score + tenure_score + kyc_score + repayment_score + dti_penalty

        # Cap score between 0 and 100
        score = max(0, min(100, score))

        # Determine risk level
        if score >= 75:
            risk_level = "LOW"
        elif score >= 50:
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
                "income": income_score,  # Use the variable directly
                "employment_type": employment_score,
                "job_tenure": tenure_score,
                "kyc_verified": kyc_score,
                "debt_to_income_penalty": dti_penalty,
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

        # Severe penalty if no payments made
        if total_paid == 0 and total_overdue > 0:
            return 0
        
        # Calculate on-time payment rate
        if total_paid > 0:
            on_time_rate = (total_paid_on_time / total_paid) * 100

        else:
            on_time_rate = 0

         # Base score (max 35)
        if on_time_rate == 100 and total_overdue ==0:
            base_score = 25
        elif on_time_rate >= 95:
            base_score = 22
        elif on_time_rate >= 90:
            base_score = 19
        elif on_time_rate >= 80:
            base_score = 15
        elif on_time_rate >= 70:
            base_score = 11
        elif on_time_rate >= 50:
            base_score = 6
        else:
            base_score = 2

        # Late payment penalty
        late_penalty = 0
        if total_late > 0:
            late_penalty = min(15, total_late * 2)

        # Overdue payment penalty
        overdue_penalty = 0
        if total_overdue > 0:
            overdue_penalty = min(20, total_overdue * 3)

        final_score = base_score - late_penalty - overdue_penalty

        return max(0, min(25, final_score))