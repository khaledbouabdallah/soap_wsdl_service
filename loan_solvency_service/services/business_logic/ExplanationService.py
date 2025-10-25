from spyne.decorator import srpc
from spyne.model.primitive import Integer, Decimal, Boolean
from loan_solvency_service.shared.base_service import SoaServiceBase
from loan_solvency_service.shared.datamodels import Explanations


class ExplanationService(SoaServiceBase):
    """
    2.2: ExplanationService - Generates human-readable explanations for solvency decision.
    """

    @srpc(Integer, Decimal, Decimal, Decimal, Integer, Boolean, _returns=Explanations)
    def Explain(
        credit_score,
        monthly_income,
        monthly_expenses,
        debt,
        late_payments,
        has_bankruptcy,
    ):
        """
        Explain(score, monthlyIncome, monthlyExpenses, debt, latePayments, hasBankruptcy) -> Explanations

        Generates three explanation strings for the solvency decision.
        """

        # 1. Credit Score Explanation
        if credit_score >= 800:
            score_explanation = (
                f"Excellent credit score of {credit_score}. Strong creditworthiness."
            )
        elif credit_score >= 700:
            score_explanation = (
                f"Good credit score of {credit_score}. Acceptable credit risk."
            )
        elif credit_score >= 500:
            score_explanation = (
                f"Fair credit score of {credit_score}. Moderate credit risk."
            )
        else:
            score_explanation = (
                f"Poor credit score of {credit_score}. High credit risk."
            )

        # 2. Income vs Expenses Explanation
        net_income = monthly_income - monthly_expenses
        if net_income > 1000:
            income_explanation = (
                f"Strong financial position with ${net_income:.2f} monthly surplus."
            )
        elif net_income > 0:
            income_explanation = (
                f"Tight budget with only ${net_income:.2f} monthly surplus."
            )
        elif net_income == 0:
            income_explanation = (
                "Break-even situation. Income exactly matches expenses."
            )
        else:
            income_explanation = f"Negative cash flow of ${abs(net_income):.2f} per month. Expenses exceed income."

        # 3. Credit History Explanation
        history_parts = []

        if debt > 0:
            history_parts.append(f"${debt:.2f} in outstanding debt")
        else:
            history_parts.append("no outstanding debt")

        if late_payments > 0:
            history_parts.append(f"{late_payments} late payment(s)")
        else:
            history_parts.append("no late payments")

        if has_bankruptcy:
            history_parts.append("bankruptcy on record")
        else:
            history_parts.append("no bankruptcy history")

        history_explanation = f"Credit history shows {', '.join(history_parts)}."

        explanations = Explanations(
            credit_score_explanation=score_explanation,
            income_vs_expenses_explanation=income_explanation,
            credit_history_explanation=history_explanation,
        )

        SoaServiceBase.log_info("Explanations generated for solvency decision")

        return explanations
