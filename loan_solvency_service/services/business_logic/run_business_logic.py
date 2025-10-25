import logging
from loan_solvency_service.services.business_logic.CreditScoringService import (
    CreditScoringService,
)
from loan_solvency_service.services.business_logic.SolvencyDecisionService import (
    SolvencyDecisionService,
)
from loan_solvency_service.services.business_logic.ExplanationService import (
    ExplanationService,
)
from loan_solvency_service.shared.base_service import start_spyne_server

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def run_business_logic_services(port=8000):
    """
    Starts the container that hosts all three business logic services.
    These are internal services used by the orchestrator.
    """
    interface_name = "BusinessLogic"

    start_spyne_server(
        service_classes=[
            CreditScoringService,
            SolvencyDecisionService,
            ExplanationService,
        ],
        interface_name=interface_name,
        port=port,
        tns_suffix=":business",
    )


if __name__ == "__main__":
    run_business_logic_services()
