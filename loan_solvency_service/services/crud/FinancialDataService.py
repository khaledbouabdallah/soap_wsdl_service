from spyne.decorator import srpc
from loan_solvency_service.shared.base_service import (
    ClientValidationError,
    SoaServiceBase,
    ClientNotFoundFault,
    validate_client_id,
)
from loan_solvency_service.shared.datamodels import (
    ClientId,
    Financials,
    map_client_to_models,
)
from loan_solvency_service.shared.db_setup import SessionLocal, Client
from sqlalchemy.orm.exc import NoResultFound


class FinancialDataService(SoaServiceBase):
    """
    2.1: FinancialDataService - Retrieves client monthly income and expenses.
    """

    @srpc(
        ClientId,
        _returns=Financials,
        _faults=[ClientNotFoundFault, ClientValidationError],
    )
    def GetClientFinancials(client_id):
        """GetClientFinancials(clientId) -> {monthlyIncome, monthlyExpenses}"""

        validate_client_id(client_id)
        db = SessionLocal()
        try:
            client_record = db.query(Client).filter(Client.client_id == client_id).one()

            # Use the shared mapping utility
            _, financials, _ = map_client_to_models(client_record)

            SoaServiceBase.log_info(f"Financials retrieved for {client_id}", client_id)
            return financials

        except NoResultFound:
            SoaServiceBase.log_error(
                f"Client ID not found for financials: {client_id}", client_id
            )
            raise ClientNotFoundFault(
                detail=f"Client with ID '{client_id}' not found in directory."
            )
        finally:
            db.close()
