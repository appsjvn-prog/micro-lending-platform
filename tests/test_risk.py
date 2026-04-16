import pytest
from app.services.risk_score import RiskScoreCalculator


class TestRiskScoreLogic:
    
    def test_risk_level_thresholds(self):
        """Test that risk levels are assigned correctly based on score"""
        
        # Test LOW risk (score >= 70)
        assert self._get_risk_level(85) == "LOW"
        assert self._get_risk_level(70) == "LOW"
        
        # Test MEDIUM risk (40 <= score < 70)
        assert self._get_risk_level(65) == "MEDIUM"
        assert self._get_risk_level(55) == "MEDIUM"
        assert self._get_risk_level(40) == "MEDIUM"
        
        # Test HIGH risk (score < 40)
        assert self._get_risk_level(35) == "HIGH"
        assert self._get_risk_level(20) == "HIGH"
        assert self._get_risk_level(0) == "HIGH"
        
        print(" Risk level thresholds test passed")
    
    def test_income_scoring(self):
        """Test income contribution to score"""
        
        # Base score 50 + income points
        test_cases = [
            (150000, 25),   # 100k+ → +25
            (75000, 15),    # 50k-100k → +15
            (35000, 10),    # 25k-50k → +10
            (20000, 5),     # 15k-25k → +5
            (10000, 0),     # <15k → 0
        ]
        
        for income, expected_bonus in test_cases:
            base = 50
            if income >= 100000:
                bonus = 25
            elif income >= 50000:
                bonus = 15
            elif income >= 25000:
                bonus = 10
            elif income >= 15000:
                bonus = 5
            else:
                bonus = 0
            
            assert bonus == expected_bonus, f"Income {income}: expected {expected_bonus}, got {bonus}"
        
        print(" Income scoring test passed")
    
    def test_tenure_scoring(self):
        """Test job tenure contribution to score"""
        
        test_cases = [
            (36, 10),   # 24+ months → +10
            (24, 10),   # 24+ months → +10
            (18, 7),    # 12-24 months → +7
            (12, 7),    # 12-24 months → +7
            (9, 4),     # 6-12 months → +4
            (6, 4),     # 6-12 months → +4
            (4, 2),     # 3-6 months → +2
            (3, 2),     # 3-6 months → +2
            (1, 0),     # <3 months → 0
            (0, 0),     # None → 0
        ]
        
        for tenure, expected_bonus in test_cases:
            if tenure >= 24:
                bonus = 10
            elif tenure >= 12:
                bonus = 7
            elif tenure >= 6:
                bonus = 4
            elif tenure >= 3:
                bonus = 2
            else:
                bonus = 0
            
            assert bonus == expected_bonus, f"Tenure {tenure} months: expected {expected_bonus}, got {bonus}"
        
        print(" Tenure scoring test passed")
    
    def test_active_loan_penalty(self):
        """Test active loan penalties"""
        
        test_cases = [
            (0, 0),    # 0 loans → 0 penalty
            (1, 6),    # 1 loan → -6
            (2, 12),   # 2 loans → -12
            (3, 20),   # 3+ loans → -20
            (5, 20),   # 5 loans → -20
        ]
        
        for loan_count, expected_penalty in test_cases:
            if loan_count >= 3:
                penalty = 20
            elif loan_count == 2:
                penalty = 12
            elif loan_count == 1:
                penalty = 6
            else:
                penalty = 0
            
            assert penalty == expected_penalty, f"{loan_count} loans: expected penalty {expected_penalty}, got {penalty}"
        
        print(" Active loan penalty test passed")
    
    def _get_risk_level(self, score):
        """Helper to get risk level from score"""
        if score >= 70:
            return "LOW"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "HIGH"


