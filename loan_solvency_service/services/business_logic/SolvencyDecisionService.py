from spyne.decorator import srpc
from spyne.model.primitive import Integer, Decimal
from loan_solvency_service.shared.base_service import SoaServiceBase
from loan_solvency_service.shared.datamodels import SolvencyStatus


class SolvencyDecisionService(SoaServiceBase):
    """
    2.2: SolvencyDecisionService - Decides solvency status based on income, expenses, and credit score.
    Rule: solvent if score >= 700 AND monthlyIncome > monthlyExpenses
    """

    @srpc(Decimal, Decimal, Integer, _returns=SolvencyStatus)
    def DecideSolvency(monthly_income, monthly_expenses, credit_score):
        """
        DecideSolvency(monthlyIncome, monthlyExpenses, score) -> SolvencyStatus

        Determines if client is solvent based on financial data and credit score.
        """
        # Apply the mandatory rule
        is_solvent = (credit_score >= 700) and (monthly_income > monthly_expenses)

        status_str = "solvent" if is_solvent else "not_solvent"

        # Create SolvencyStatus ComplexModel
        status = SolvencyStatus(status=status_str)

        SoaServiceBase.log_info(
            f"Solvency decision: {status_str} (income={monthly_income}, expenses={monthly_expenses}, score={credit_score})"
        )

        return status
