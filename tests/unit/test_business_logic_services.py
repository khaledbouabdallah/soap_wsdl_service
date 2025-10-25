import pytest
from decimal import Decimal
from loan_solvency_service.services.business_logic.CreditScoringService import (
    CreditScoringService,
)
from loan_solvency_service.services.business_logic.SolvencyDecisionService import (
    SolvencyDecisionService,
)
from loan_solvency_service.services.business_logic.ExplanationService import (
    ExplanationService,
)

# ============================================
# Tests for CreditScoringService
# ============================================


def test_compute_credit_score_no_issues():
    """Test score with no debt, no late payments, no bankruptcy"""
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("0"), late_payments=0, has_bankruptcy=False
    )
    assert score == 1000


def test_compute_credit_score_with_debt():
    """Test score calculation with debt only"""
    # 1000 - 0.1*5000 = 500
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("5000"), late_payments=0, has_bankruptcy=False
    )
    assert score == 500


def test_compute_credit_score_with_late_payments():
    """Test score calculation with late payments only"""
    # 1000 - 50*2 = 900
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("0"), late_payments=2, has_bankruptcy=False
    )
    assert score == 900


def test_compute_credit_score_with_bankruptcy():
    """Test score calculation with bankruptcy only"""
    # 1000 - 200 = 800
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("0"), late_payments=0, has_bankruptcy=True
    )
    assert score == 800


def test_compute_credit_score_client_001():
    """Test with client-001 data: should get score 400"""
    # debt=5000, late=2, bankruptcy=false
    # 1000 - 0.1*5000 - 50*2 - 0 = 1000 - 500 - 100 = 400
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("5000"), late_payments=2, has_bankruptcy=False
    )
    assert score == 400


def test_compute_credit_score_client_002():
    """Test with client-002 data: should get score 800"""
    # debt=2000, late=0, bankruptcy=false
    # 1000 - 0.1*2000 - 0 - 0 = 1000 - 200 = 800
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("2000"), late_payments=0, has_bankruptcy=False
    )
    assert score == 800


def test_compute_credit_score_client_003():
    """Test with client-003 data: should get negative score clamped to 0"""
    # debt=10000, late=5, bankruptcy=true
    # 1000 - 0.1*10000 - 50*5 - 200 = 1000 - 1000 - 250 - 200 = -450 -> clamped to 0
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("10000"), late_payments=5, has_bankruptcy=True
    )
    assert score == 0  # Should be clamped to minimum


def test_compute_credit_score_clamping_upper():
    """Test that score doesn't exceed 1000"""
    # Even with negative debt (edge case), score should not exceed 1000
    score = CreditScoringService.ComputeCreditScore(
        debt=Decimal("0"), late_payments=0, has_bankruptcy=False
    )
    assert score <= 1000


# ============================================
# Tests for SolvencyDecisionService
# ============================================


def test_decide_solvency_solvent():
    """Test solvent case: score >= 700 and income > expenses"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("4000"),
        monthly_expenses=Decimal("3000"),
        credit_score=800,
    )
    assert result.status == "solvent"


def test_decide_solvency_not_solvent_low_score():
    """Test not solvent due to low credit score"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("5000"),
        monthly_expenses=Decimal("3000"),
        credit_score=650,  # Below 700
    )
    assert result.status == "not_solvent"


def test_decide_solvency_not_solvent_expenses_exceed_income():
    """Test not solvent due to expenses >= income"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("3500"),
        credit_score=800,  # Good score but expenses too high
    )
    assert result.status == "not_solvent"


def test_decide_solvency_not_solvent_break_even():
    """Test not solvent when income equals expenses (not greater)"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("3000"),  # Equal
        credit_score=750,
    )
    assert result.status == "not_solvent"


def test_decide_solvency_client_001():
    """Test client-001: score 400, income > expenses -> not_solvent (low score)"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("4000"),
        monthly_expenses=Decimal("3000"),
        credit_score=400,
    )
    assert result.status == "not_solvent"


def test_decide_solvency_client_002():
    """Test client-002: score 800, income > expenses -> solvent"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("2500"),
        credit_score=800,
    )
    assert result.status == "solvent"


def test_decide_solvency_client_003():
    """Test client-003: score 0, income > expenses -> not_solvent (low score)"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("6000"), monthly_expenses=Decimal("5500"), credit_score=0
    )
    assert result.status == "not_solvent"


def test_decide_solvency_boundary_score_700():
    """Test boundary: score exactly 700 with income > expenses -> solvent"""
    result = SolvencyDecisionService.DecideSolvency(
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("2000"),
        credit_score=700,  # Exactly at threshold
    )
    assert result.status == "solvent"


# ============================================
# Tests for ExplanationService
# ============================================


def test_explain_generates_three_explanations():
    """Test that Explain returns all three required explanation fields"""
    result = ExplanationService.Explain(
        credit_score=800,
        monthly_income=Decimal("4000"),
        monthly_expenses=Decimal("3000"),
        debt=Decimal("5000"),
        late_payments=2,
        has_bankruptcy=False,
    )

    assert result.credit_score_explanation is not None
    assert result.income_vs_expenses_explanation is not None
    assert result.credit_history_explanation is not None


def test_explain_all_fields_non_empty():
    """Test that all explanation fields are non-empty strings"""
    result = ExplanationService.Explain(
        credit_score=500,
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("3500"),
        debt=Decimal("10000"),
        late_payments=5,
        has_bankruptcy=True,
    )

    # XSD requires minLength=1
    assert len(result.credit_score_explanation) > 0
    assert len(result.income_vs_expenses_explanation) > 0
    assert len(result.credit_history_explanation) > 0


def test_explain_excellent_credit_score():
    """Test explanation for excellent credit score (>= 800)"""
    result = ExplanationService.Explain(
        credit_score=850,
        monthly_income=Decimal("5000"),
        monthly_expenses=Decimal("3000"),
        debt=Decimal("0"),
        late_payments=0,
        has_bankruptcy=False,
    )

    assert (
        "excellent" in result.credit_score_explanation.lower()
        or "850" in result.credit_score_explanation
    )


def test_explain_poor_credit_score():
    """Test explanation for poor credit score (< 500)"""
    result = ExplanationService.Explain(
        credit_score=300,
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("2000"),
        debt=Decimal("15000"),
        late_payments=10,
        has_bankruptcy=True,
    )

    assert (
        "poor" in result.credit_score_explanation.lower()
        or "300" in result.credit_score_explanation
    )


def test_explain_positive_cash_flow():
    """Test explanation mentions surplus when income > expenses"""
    result = ExplanationService.Explain(
        credit_score=700,
        monthly_income=Decimal("5000"),
        monthly_expenses=Decimal("3000"),
        debt=Decimal("2000"),
        late_payments=0,
        has_bankruptcy=False,
    )

    assert "surplus" in result.income_vs_expenses_explanation.lower()


def test_explain_negative_cash_flow():
    """Test explanation mentions deficit when expenses > income"""
    result = ExplanationService.Explain(
        credit_score=700,
        monthly_income=Decimal("2000"),
        monthly_expenses=Decimal("3000"),
        debt=Decimal("5000"),
        late_payments=2,
        has_bankruptcy=False,
    )

    assert (
        "negative" in result.income_vs_expenses_explanation.lower()
        or "exceed" in result.income_vs_expenses_explanation.lower()
    )


def test_explain_bankruptcy_mentioned():
    """Test that bankruptcy is mentioned in credit history explanation"""
    result = ExplanationService.Explain(
        credit_score=400,
        monthly_income=Decimal("3000"),
        monthly_expenses=Decimal("2500"),
        debt=Decimal("10000"),
        late_payments=5,
        has_bankruptcy=True,
    )

    assert "bankruptcy" in result.credit_history_explanation.lower()


def test_explain_no_issues_clean_record():
    """Test explanation for clean credit record"""
    result = ExplanationService.Explain(
        credit_score=1000,
        monthly_income=Decimal("5000"),
        monthly_expenses=Decimal("2000"),
        debt=Decimal("0"),
        late_payments=0,
        has_bankruptcy=False,
    )

    # Should mention no debt, no late payments, no bankruptcy
    history_lower = result.credit_history_explanation.lower()
    assert "no" in history_lower or "0" in result.credit_history_explanation
