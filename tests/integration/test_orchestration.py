import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loan_solvency_service.shared.db_setup import Base, Client
from loan_solvency_service.services.orchestration.SolvencyVerificationService import (
    SolvencyVerificationService,
)
from loan_solvency_service.shared.base_service import ClientNotFoundFault
from loan_solvency_service.shared import db_setup

# Test data matching project requirements
TEST_CLIENTS = [
    {
        "client_id": "client-001",
        "name": "John Doe",
        "address": "123 Main St",
        "monthly_income": Decimal("4000.00"),
        "monthly_expenses": Decimal("3000.00"),
        "debt": Decimal("5000.00"),
        "late_payments": 2,
        "has_bankruptcy": False,
    },
    {
        "client_id": "client-002",
        "name": "Alice Smith",
        "address": "456 Elm St",
        "monthly_income": Decimal("3000.00"),
        "monthly_expenses": Decimal("2500.00"),
        "debt": Decimal("2000.00"),
        "late_payments": 0,
        "has_bankruptcy": False,
    },
    {
        "client_id": "client-003",
        "name": "Bob Johnson",
        "address": "789 Oak St",
        "monthly_income": Decimal("6000.00"),
        "monthly_expenses": Decimal("5500.00"),
        "debt": Decimal("10000.00"),
        "late_payments": 5,
        "has_bankruptcy": True,
    },
]


@pytest.fixture(scope="function")
def test_db():
    """
    Creates an in-memory SQLite database for isolated testing.
    Each test gets a fresh database.
    """
    # Create in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Override the global SessionLocal used by services
    original_session = db_setup.SessionLocal
    db_setup.SessionLocal = TestSessionLocal

    # Insert test data
    session = TestSessionLocal()
    for client_data in TEST_CLIENTS:
        client = Client(**client_data)
        session.add(client)
    session.commit()
    session.close()

    yield TestSessionLocal

    # Cleanup: restore original session and close engine
    db_setup.SessionLocal = original_session
    engine.dispose()


# ============================================
# Integration Tests for Full Orchestration
# ============================================


def test_verify_solvency_client_001_not_solvent(test_db):
    """
    Test client-001: John Doe
    Expected: score 400 -> not_solvent
    Formula: 1000 - 0.1*5000 - 50*2 - 0 = 400
    Decision: 400 < 700 -> not_solvent (even though income > expenses)
    """
    report = SolvencyVerificationService.VerifySolvency("client-001")

    # Verify identity
    assert report.client_identity.name == "John Doe"
    assert report.client_identity.address == "123 Main St"

    # Verify financials
    assert report.financials.monthly_income == Decimal("4000.00")
    assert report.financials.monthly_expenses == Decimal("3000.00")

    # Verify credit history
    assert report.credit_history.debt == Decimal("5000.00")
    assert report.credit_history.late_payments == 2
    assert report.credit_history.has_bankruptcy is False

    # Verify credit score
    assert report.credit_score == 400

    # Verify solvency status
    assert report.solvency_status.status == "not_solvent"

    # Verify explanations exist and are non-empty
    assert len(report.explanations.credit_score_explanation) > 0
    assert len(report.explanations.income_vs_expenses_explanation) > 0
    assert len(report.explanations.credit_history_explanation) > 0


def test_verify_solvency_client_002_solvent(test_db):
    """
    Test client-002: Alice Smith
    Expected: score 800 -> solvent
    Formula: 1000 - 0.1*2000 - 0 - 0 = 800
    Decision: 800 >= 700 AND 3000 > 2500 -> solvent
    """
    report = SolvencyVerificationService.VerifySolvency("client-002")

    # Verify identity
    assert report.client_identity.name == "Alice Smith"
    assert report.client_identity.address == "456 Elm St"

    # Verify financials
    assert report.financials.monthly_income == Decimal("3000.00")
    assert report.financials.monthly_expenses == Decimal("2500.00")

    # Verify credit history
    assert report.credit_history.debt == Decimal("2000.00")
    assert report.credit_history.late_payments == 0
    assert report.credit_history.has_bankruptcy is False

    # Verify credit score
    assert report.credit_score == 800

    # Verify solvency status
    assert report.solvency_status.status == "solvent"

    # Verify explanations exist
    assert len(report.explanations.credit_score_explanation) > 0
    assert len(report.explanations.income_vs_expenses_explanation) > 0
    assert len(report.explanations.credit_history_explanation) > 0


def test_verify_solvency_client_003_not_solvent(test_db):
    """
    Test client-003: Bob Johnson
    Expected: score -450 clamped to 0 -> not_solvent
    Formula: 1000 - 0.1*10000 - 50*5 - 200 = -450 -> 0
    Decision: 0 < 700 -> not_solvent
    """
    report = SolvencyVerificationService.VerifySolvency("client-003")

    # Verify identity
    assert report.client_identity.name == "Bob Johnson"
    assert report.client_identity.address == "789 Oak St"

    # Verify financials
    assert report.financials.monthly_income == Decimal("6000.00")
    assert report.financials.monthly_expenses == Decimal("5500.00")

    # Verify credit history
    assert report.credit_history.debt == Decimal("10000.00")
    assert report.credit_history.late_payments == 5
    assert report.credit_history.has_bankruptcy is True

    # Verify credit score (should be clamped to 0)
    assert report.credit_score == 0

    # Verify solvency status
    assert report.solvency_status.status == "not_solvent"

    # Verify explanations exist
    assert len(report.explanations.credit_score_explanation) > 0
    assert len(report.explanations.income_vs_expenses_explanation) > 0
    assert len(report.explanations.credit_history_explanation) > 0

    # Verify bankruptcy is mentioned
    assert "bankruptcy" in report.explanations.credit_history_explanation.lower()


def test_verify_solvency_client_not_found(test_db):
    """Test that non-existent client raises ClientNotFoundFault"""
    with pytest.raises(ClientNotFoundFault) as exc_info:
        SolvencyVerificationService.VerifySolvency("client-999")

    assert "not found" in str(exc_info.value).lower()


def test_verify_solvency_report_structure(test_db):
    """Test that the returned report has all required fields"""
    report = SolvencyVerificationService.VerifySolvency("client-002")

    # Verify all top-level fields exist
    assert hasattr(report, "client_identity")
    assert hasattr(report, "financials")
    assert hasattr(report, "credit_history")
    assert hasattr(report, "credit_score")
    assert hasattr(report, "solvency_status")
    assert hasattr(report, "explanations")

    # Verify nested structures
    assert hasattr(report.client_identity, "name")
    assert hasattr(report.client_identity, "address")
    assert hasattr(report.financials, "monthly_income")
    assert hasattr(report.financials, "monthly_expenses")
    assert hasattr(report.credit_history, "debt")
    assert hasattr(report.credit_history, "late_payments")
    assert hasattr(report.credit_history, "has_bankruptcy")
    assert hasattr(report.solvency_status, "status")
    assert hasattr(report.explanations, "credit_score_explanation")
    assert hasattr(report.explanations, "income_vs_expenses_explanation")
    assert hasattr(report.explanations, "credit_history_explanation")


def test_verify_solvency_data_types(test_db):
    """Test that all data types in the report match specifications"""
    report = SolvencyVerificationService.VerifySolvency("client-001")

    # Check types
    assert isinstance(report.client_identity.name, str)
    assert isinstance(report.client_identity.address, str)
    assert isinstance(report.financials.monthly_income, Decimal)
    assert isinstance(report.financials.monthly_expenses, Decimal)
    assert isinstance(report.credit_history.debt, Decimal)
    assert isinstance(report.credit_history.late_payments, int)
    assert isinstance(report.credit_history.has_bankruptcy, bool)
    assert isinstance(report.credit_score, int)
    assert isinstance(report.solvency_status.status, str)
    assert isinstance(report.explanations.credit_score_explanation, str)
    assert isinstance(report.explanations.income_vs_expenses_explanation, str)
    assert isinstance(report.explanations.credit_history_explanation, str)


def test_verify_solvency_score_range(test_db):
    """Test that credit score is within valid range [0, 1000]"""
    for client_data in TEST_CLIENTS:
        report = SolvencyVerificationService.VerifySolvency(client_data["client_id"])
        assert 0 <= report.credit_score <= 1000


def test_verify_solvency_status_values(test_db):
    """Test that solvency status only contains valid enum values"""
    for client_data in TEST_CLIENTS:
        report = SolvencyVerificationService.VerifySolvency(client_data["client_id"])
        assert report.solvency_status.status in ["solvent", "not_solvent"]


def test_verify_solvency_explanations_content(test_db):
    """Test that explanations contain relevant information"""
    report = SolvencyVerificationService.VerifySolvency("client-001")

    # Score should be mentioned in credit score explanation
    assert "400" in report.explanations.credit_score_explanation

    # Income/expenses should be reflected in income explanation
    assert (
        "1000" in report.explanations.income_vs_expenses_explanation
        or "surplus" in report.explanations.income_vs_expenses_explanation.lower()
    )

    # Credit history should mention debt and late payments
    credit_history_lower = report.explanations.credit_history_explanation.lower()
    assert (
        "debt" in credit_history_lower
        or "5000" in report.explanations.credit_history_explanation
    )
    assert (
        "late" in credit_history_lower
        or "2" in report.explanations.credit_history_explanation
    )


def test_verify_solvency_idempotence(test_db):
    """Test that calling VerifySolvency multiple times returns same result"""
    report1 = SolvencyVerificationService.VerifySolvency("client-002")
    report2 = SolvencyVerificationService.VerifySolvency("client-002")

    # Should return identical results
    assert report1.client_identity.name == report2.client_identity.name
    assert report1.credit_score == report2.credit_score
    assert report1.solvency_status.status == report2.solvency_status.status
