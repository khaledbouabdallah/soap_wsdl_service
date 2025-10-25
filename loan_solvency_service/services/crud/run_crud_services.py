import logging

# Import the services
from loan_solvency_service.services.crud.ClientDirectoryService import (
    ClientDirectoryService,
)
from loan_solvency_service.services.crud.FinancialDataService import (
    FinancialDataService,
)
from loan_solvency_service.services.crud.CreditBureauService import CreditBureauService

# Use the fixed server runner
from loan_solvency_service.shared.base_service import start_spyne_server

logger = logging.getLogger(__name__)
# Ensure logging is configured for the module
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def run_crud_services(port=8000):
    """
    Starts the container that hosts all three CRUD services.
    They are exposed as one Spyne Application endpoint.
    """
    interface_name = "CRUDAccess"

    start_spyne_server(
        service_classes=[
            ClientDirectoryService,
            FinancialDataService,
            CreditBureauService,
        ],
        interface_name=interface_name,
        tns_suffix=":crud",
    )


if __name__ == "__main__":
    run_crud_services()
