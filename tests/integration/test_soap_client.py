"""
Integration tests for SOAP client using zeep.

Prerequisites:
- Run `docker-compose up` before running these tests
- Services must be running at http://localhost:8000

Run with: pytest tests/integration/test_soap_client.py -v
"""

import pytest
from zeep import Client
from zeep.exceptions import Fault
from decimal import Decimal

# SOAP endpoint URL
WSDL_URL = "http://localhost:8000/SolvencyVerification?wsdl"


@pytest.fixture(scope="module")
def soap_client():
    """
    Create a zeep SOAP client connected to the running service.
    Scope is module so client is reused across all tests.
    """
    try:
        client = Client(WSDL_URL)
        return client
    except Exception as e:
        pytest.skip(
            f"Could not connect to SOAP service at {WSDL_URL}. Make sure docker-compose is running. Error: {e}"
        )


# ============================================
# Happy Path Tests - All 3 Required Clients
# ============================================


def test_verify_solvency_client_001_not_solvent(soap_client):
    """
    Test client-001: John Doe
    Expected: score 400 -> not_solvent
    """
    response = soap_client.service.VerifySolvency(client_id="client-001")

    # Verify identity
    assert response.client_identity.name == "John Doe"
    assert response.client_identity.address == "123 Main St"

    # Verify financials
    assert float(response.financials.monthly_income) == 4000.00
    assert float(response.financials.monthly_expenses) == 3000.00

    # Verify credit history
    assert float(response.credit_history.debt) == 5000.00
    assert response.credit_history.late_payments == 2
    assert response.credit_history.has_bankruptcy is False

    # Verify credit score
    assert response.credit_score == 400

    # FIXED: Access status attribute directly from ComplexModel
    assert response.solvency_status.status == "not_solvent"

    # Verify explanations exist and are non-empty
    assert len(response.explanations.credit_score_explanation) > 0
    assert len(response.explanations.income_vs_expenses_explanation) > 0
    assert len(response.explanations.credit_history_explanation) > 0


def test_verify_solvency_client_002_solvent(soap_client):
    """
    Test client-002: Alice Smith
    Expected: score 800 -> solvent
    """
    response = soap_client.service.VerifySolvency(client_id="client-002")

    # Verify identity
    assert response.client_identity.name == "Alice Smith"
    assert response.client_identity.address == "456 Elm St"

    # Verify financials
    assert float(response.financials.monthly_income) == 3000.00
    assert float(response.financials.monthly_expenses) == 2500.00

    # Verify credit history
    assert float(response.credit_history.debt) == 2000.00
    assert response.credit_history.late_payments == 0
    assert response.credit_history.has_bankruptcy is False

    # Verify credit score
    assert response.credit_score == 800

    # FIXED: Access status attribute directly from ComplexModel
    assert response.solvency_status.status == "solvent"

    # Verify explanations
    assert len(response.explanations.credit_score_explanation) > 0
    assert len(response.explanations.income_vs_expenses_explanation) > 0
    assert len(response.explanations.credit_history_explanation) > 0


def test_verify_solvency_client_003_not_solvent(soap_client):
    """
    Test client-003: Bob Johnson
    Expected: score 0 (clamped from -450) -> not_solvent
    """
    response = soap_client.service.VerifySolvency(client_id="client-003")

    # Verify identity
    assert response.client_identity.name == "Bob Johnson"
    assert response.client_identity.address == "789 Oak St"

    # Verify financials
    assert float(response.financials.monthly_income) == 6000.00
    assert float(response.financials.monthly_expenses) == 5500.00

    # Verify credit history
    assert float(response.credit_history.debt) == 10000.00
    assert response.credit_history.late_payments == 5
    assert response.credit_history.has_bankruptcy is True

    # Verify credit score (clamped to 0)
    assert response.credit_score == 0

    # FIXED: Access status attribute directly from ComplexModel
    assert response.solvency_status.status == "not_solvent"

    # Verify bankruptcy is mentioned in explanations
    assert "bankruptcy" in response.explanations.credit_history_explanation.lower()


# ============================================
# SOAP Fault Tests
# ============================================


def test_verify_solvency_client_not_found(soap_client):
    """
    Test that non-existent client raises SOAP Fault Client.NotFound
    Valid pattern but doesn't exist in database
    """
    with pytest.raises(Fault) as exc_info:
        soap_client.service.VerifySolvency(client_id="client-999")

    # Verify it's the correct fault code
    error_str = str(exc_info.value).lower()
    assert "notfound" in error_str or "not found" in error_str


def test_verify_solvency_invalid_client_id_pattern(soap_client):
    """
    Test that invalid client ID pattern raises SOAP Fault Client.ValidationError
    Invalid pattern should be caught before database lookup
    """
    with pytest.raises(Fault) as exc_info:
        # This should fail validation (pattern: client-\d{3})
        soap_client.service.VerifySolvency(client_id="invalid-id")

    # FIXED: Should be ValidationError for invalid pattern
    error_msg = str(exc_info.value).lower()
    assert "validation" in error_msg or "invalid" in error_msg or "pattern" in error_msg


# ============================================
# Data Structure & Type Tests
# ============================================


def test_soap_response_structure(soap_client):
    """
    Test that SOAP response has all required fields per XSD
    """
    response = soap_client.service.VerifySolvency(client_id="client-002")

    # Verify all top-level fields exist
    assert hasattr(response, "client_identity")
    assert hasattr(response, "financials")
    assert hasattr(response, "credit_history")
    assert hasattr(response, "credit_score")
    assert hasattr(response, "solvency_status")
    assert hasattr(response, "explanations")

    # Verify nested structures
    assert hasattr(response.client_identity, "name")
    assert hasattr(response.client_identity, "address")
    assert hasattr(response.financials, "monthly_income")
    assert hasattr(response.financials, "monthly_expenses")
    assert hasattr(response.credit_history, "debt")
    assert hasattr(response.credit_history, "late_payments")
    assert hasattr(response.credit_history, "has_bankruptcy")
    assert hasattr(response.explanations, "credit_score_explanation")
    assert hasattr(response.explanations, "income_vs_expenses_explanation")
    assert hasattr(response.explanations, "credit_history_explanation")


def test_soap_credit_score_range(soap_client):
    """
    Test that credit score is within valid XSD range [0, 1000]
    """
    test_clients = ["client-001", "client-002", "client-003"]

    for client_id in test_clients:
        response = soap_client.service.VerifySolvency(client_id=client_id)
        assert (
            0 <= response.credit_score <= 1000
        ), f"Score {response.credit_score} out of range for {client_id}"


def test_soap_solvency_status_enum(soap_client):
    """
    Test that solvency status only contains valid enum values per XSD
    """
    test_clients = ["client-001", "client-002", "client-003"]

    for client_id in test_clients:
        response = soap_client.service.VerifySolvency(client_id=client_id)
        # FIXED: Access status attribute directly from ComplexModel
        assert response.solvency_status.status in [
            "solvent",
            "not_solvent",
        ], f"Invalid status for {client_id}"


def test_soap_explanations_non_empty(soap_client):
    """
    Test that all explanation strings are non-empty per XSD minLength constraint
    """
    response = soap_client.service.VerifySolvency(client_id="client-001")

    # XSD requires minLength=1 for all explanation fields
    assert len(response.explanations.credit_score_explanation) > 0
    assert len(response.explanations.income_vs_expenses_explanation) > 0
    assert len(response.explanations.credit_history_explanation) > 0


# ============================================
# Idempotence & Consistency Tests
# ============================================


def test_soap_idempotence(soap_client):
    """
    Test that calling the same operation multiple times returns identical results
    """
    response1 = soap_client.service.VerifySolvency(client_id="client-002")
    response2 = soap_client.service.VerifySolvency(client_id="client-002")

    # FIXED: Access status attribute directly from ComplexModel
    # Should return identical results
    assert response1.client_identity.name == response2.client_identity.name
    assert response1.credit_score == response2.credit_score
    assert response1.solvency_status.status == response2.solvency_status.status


def test_soap_financial_calculations_consistency(soap_client):
    """
    Test that the financial data is consistent with the decision
    """
    # client-002: income=3000, expenses=2500, score=800
    # Should be solvent (score >= 700 AND income > expenses)
    response = soap_client.service.VerifySolvency(client_id="client-002")

    income = float(response.financials.monthly_income)
    expenses = float(response.financials.monthly_expenses)
    score = response.credit_score
    # FIXED: Access status attribute directly from ComplexModel
    status = response.solvency_status.status

    # Verify decision logic
    expected_solvent = (score >= 700) and (income > expenses)
    expected_status = "solvent" if expected_solvent else "not_solvent"

    assert (
        status == expected_status
    ), f"Decision inconsistent: score={score}, income={income}, expenses={expenses}"


# ============================================
# WSDL & Service Discovery Tests
# ============================================


def test_wsdl_accessible():
    """
    Test that WSDL is accessible and can be parsed
    """
    try:
        client = Client(WSDL_URL)
        assert client is not None
        assert client.wsdl is not None
    except Exception as e:
        pytest.fail(f"WSDL not accessible or invalid: {e}")


def test_soap_service_operations(soap_client):
    """
    Test that the expected operations are available in the WSDL
    """
    # Get the service binding
    service = soap_client.service

    # VerifySolvency should be available
    assert hasattr(
        service, "VerifySolvency"
    ), "VerifySolvency operation not found in WSDL"
