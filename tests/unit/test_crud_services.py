import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loan_solvency_service.shared.db_setup import Base, Client
from loan_solvency_service.services.crud.ClientDirectoryService import (
    ClientDirectoryService,
)
from loan_solvency_service.services.crud.FinancialDataService import (
    FinancialDataService,
)
from loan_solvency_service.services.crud.CreditBureauService import CreditBureauService
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
# Tests for ClientDirectoryService
# ============================================


def test_get_client_identity_success(test_db):
    """Test successful retrieval of client identity"""
    # Test client-001
    result = ClientDirectoryService.GetClientIdentity("client-001")

    assert result is not None
    assert result.name == "John Doe"
    assert result.address == "123 Main St"


def test_get_client_identity_all_clients(test_db):
    """Test that all three test clients can be retrieved"""
    # Test all clients
    for test_client in TEST_CLIENTS:
        result = ClientDirectoryService.GetClientIdentity(test_client["client_id"])
        assert result.name == test_client["name"]
        assert result.address == test_client["address"]


def test_get_client_identity_not_found(test_db):
    """Test that non-existent client raises ClientNotFoundFault"""
    with pytest.raises(ClientNotFoundFault) as exc_info:
        ClientDirectoryService.GetClientIdentity("client-999")

    assert "not found" in str(exc_info.value).lower()
    assert "client-999" in str(exc_info.value)


# ============================================
# Tests for FinancialDataService
# ============================================


def test_get_client_financials_success(test_db):
    """Test successful retrieval of client financials"""
    # Test client-002
    result = FinancialDataService.GetClientFinancials("client-002")

    assert result is not None
    assert result.monthly_income == Decimal("3000.00")
    assert result.monthly_expenses == Decimal("2500.00")


def test_get_client_financials_all_clients(test_db):
    """Test financial data for all test clients"""
    for test_client in TEST_CLIENTS:
        result = FinancialDataService.GetClientFinancials(test_client["client_id"])
        assert result.monthly_income == test_client["monthly_income"]
        assert result.monthly_expenses == test_client["monthly_expenses"]


def test_get_client_financials_not_found(test_db):
    """Test that non-existent client raises ClientNotFoundFault"""
    with pytest.raises(ClientNotFoundFault) as exc_info:
        FinancialDataService.GetClientFinancials("client-invalid")

    assert "not found" in str(exc_info.value).lower()


# ============================================
# Tests for CreditBureauService
# ============================================


def test_get_client_credit_history_success(test_db):
    """Test successful retrieval of credit history"""
    # Test client-003 (has bankruptcy)
    result = CreditBureauService.GetClientCreditHistory("client-003")

    assert result is not None
    assert result.debt == Decimal("10000.00")
    assert result.late_payments == 5
    assert result.has_bankruptcy is True


def test_get_client_credit_history_all_clients(test_db):
    """Test credit history for all test clients"""
    for test_client in TEST_CLIENTS:
        result = CreditBureauService.GetClientCreditHistory(test_client["client_id"])
        assert result.debt == test_client["debt"]
        assert result.late_payments == test_client["late_payments"]
        assert result.has_bankruptcy == test_client["has_bankruptcy"]


def test_get_client_credit_history_no_bankruptcy(test_db):
    """Test client with no bankruptcy history"""
    # client-001 has no bankruptcy
    result = CreditBureauService.GetClientCreditHistory("client-001")

    assert result.has_bankruptcy is False
    assert result.late_payments == 2
    assert result.debt == Decimal("5000.00")


def test_get_client_credit_history_not_found(test_db):
    """Test that non-existent client raises ClientNotFoundFault"""
    with pytest.raises(ClientNotFoundFault) as exc_info:
        CreditBureauService.GetClientCreditHistory("client-000")

    assert "not found" in str(exc_info.value).lower()


# ============================================
# Edge Cases & Data Validation
# ============================================


def test_data_types_are_correct(test_db):
    """Verify that returned data types match Spyne ComplexModel specifications"""
    identity = ClientDirectoryService.GetClientIdentity("client-001")
    financials = FinancialDataService.GetClientFinancials("client-001")
    history = CreditBureauService.GetClientCreditHistory("client-001")

    # Check types
    assert isinstance(identity.name, str)
    assert isinstance(identity.address, str)
    assert isinstance(financials.monthly_income, Decimal)
    assert isinstance(financials.monthly_expenses, Decimal)
    assert isinstance(history.debt, Decimal)
    assert isinstance(history.late_payments, int)
    assert isinstance(history.has_bankruptcy, bool)


def test_decimal_precision(test_db):
    """Verify decimal values maintain correct precision"""
    financials = FinancialDataService.GetClientFinancials("client-002")

    # Check that decimals are precise
    assert financials.monthly_income == Decimal("3000.00")
    assert financials.monthly_expenses == Decimal("2500.00")

    # Verify no floating point errors
    assert str(financials.monthly_income) == "3000.00"
