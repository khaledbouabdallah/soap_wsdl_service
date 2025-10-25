from spyne.decorator import srpc
from spyne.model.primitive import Integer, Decimal, Boolean
from loan_solvency_service.shared.base_service import SoaServiceBase


class CreditScoringService(SoaServiceBase):
    """
    2.2: CreditScoringService - Computes credit score based on debt, late payments, and bankruptcy.
    Formula: score = 1000 - 0.1*debt - 50*latePayments - (hasBankruptcy ? 200 : 0)
    """

    @srpc(Decimal, Integer, Boolean, _returns=Integer)
    def ComputeCreditScore(debt, late_payments, has_bankruptcy):
        """
        ComputeCreditScore(debt, latePayments, hasBankruptcy) -> score

        Returns credit score between 0-1000 based on credit history.
        """
        # Apply the mandatory formula
        score = 1000 - (0.1 * float(debt)) - (50 * late_payments)

        if has_bankruptcy:
            score -= 200

        # Clamp score to valid range [0, 1000]
        score = max(0, min(1000, int(score)))

        SoaServiceBase.log_info(
            f"Credit score computed: {score} (debt={debt}, late={late_payments}, bankruptcy={has_bankruptcy})"
        )

        return score
