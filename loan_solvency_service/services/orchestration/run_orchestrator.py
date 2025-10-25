import logging
from loan_solvency_service.services.orchestration.SolvencyVerificationService import (
    SolvencyVerificationService,
)
from loan_solvency_service.shared.base_service import start_spyne_server

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def run_orchestrator(port=8000):
    """
    Starts the main orchestration service that exposes VerifySolvency operation.
    This is the public-facing SOAP endpoint.
    """
    interface_name = "SolvencyVerification"

    start_spyne_server(
        service_classes=[SolvencyVerificationService],
        interface_name=interface_name,
        port=port,
        tns_suffix="",
    )


if __name__ == "__main__":
    run_orchestrator()
