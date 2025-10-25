from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode, Integer, Decimal, Boolean
from enum import Enum as PyEnum
import logging

logger = logging.getLogger(__name__)

# --- Simple Types ---
ClientId = Unicode


# --- Python Enum for Type Safety ---
class SolvencyStatusEnum(PyEnum):
    """Python enum for internal type safety"""

    SOLVENT = "solvent"
    NOT_SOLVENT = "not_solvent"


# --- Complex Types (Matching XSD Structure) ---
class ClientIdentity(ComplexModel):
    """3.1: ClientIdentity (name, address)"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    name = Unicode
    address = Unicode


class Financials(ComplexModel):
    """3.1: Financials (monthlyIncome, monthlyExpenses)"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    monthly_income = Decimal
    monthly_expenses = Decimal


class CreditHistory(ComplexModel):
    """3.1: CreditHistory (debt, latePayments, hasBankruptcy)"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    debt = Decimal
    late_payments = Integer
    has_bankruptcy = Boolean


class SolvencyStatus(ComplexModel):
    """3.1: SolvencyStatus - using Unicode with validation"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    # Changed: Using Unicode instead of Enum
    # The XSD will enforce the enumeration constraint
    status = Unicode(values=["solvent", "not_solvent"])


class Explanations(ComplexModel):
    """3.1: Explanations (3 non empty strings)"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    credit_score_explanation = Unicode
    income_vs_expenses_explanation = Unicode
    credit_history_explanation = Unicode


class SolvencyReport(ComplexModel):
    """3.1: SolvencyReport (aggregation)"""

    __namespace__ = "urn:solvency.verification.service:datatypes:v1"
    client_identity = ClientIdentity
    financials = Financials
    credit_history = CreditHistory
    credit_score = Integer
    # Changed: Now expects a SolvencyStatus ComplexModel
    solvency_status = SolvencyStatus
    explanations = Explanations


# Validation helper
def validate_solvency_status(status_str):
    """Validates that status string is one of the allowed values"""
    allowed = ["solvent", "not_solvent"]
    if status_str not in allowed:
        raise ValueError(
            f"Invalid solvency status: {status_str}. Must be one of {allowed}"
        )
    return status_str


# Mapping utility to convert SQLAlchemy model to Spyne ComplexModel
def map_client_to_models(client_record):
    """Converts a SQLAlchemy Client record into its three Spyne ComplexModel parts."""
    if not client_record:
        return None, None, None

    identity = ClientIdentity(name=client_record.name, address=client_record.address)

    financials = Financials(
        monthly_income=client_record.monthly_income,
        monthly_expenses=client_record.monthly_expenses,
    )

    history = CreditHistory(
        debt=client_record.debt,
        late_payments=client_record.late_payments,
        has_bankruptcy=client_record.has_bankruptcy,
    )

    return identity, financials, history
