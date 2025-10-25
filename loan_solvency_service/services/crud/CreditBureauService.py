from spyne.decorator import srpc
from loan_solvency_service.shared.base_service import (
    SoaServiceBase,
    ClientNotFoundFault,
    ClientValidationError,
    validate_client_id,
)
from loan_solvency_service.shared.datamodels import (
    ClientId,
    CreditHistory,
    map_client_to_models,
)
from loan_solvency_service.shared.db_setup import SessionLocal, Client
from sqlalchemy.orm.exc import NoResultFound


class CreditBureauService(SoaServiceBase):
    """
    2.1: CreditBureauService - Retrieves client credit history.
    """

    @srpc(
        ClientId,
        _returns=CreditHistory,
        _faults=[ClientNotFoundFault, ClientValidationError],
    )
    def GetClientCreditHistory(client_id):
        """GetClientCreditHistory(clientId) -> {debt, latePayments, hasBankruptcy}"""

        validate_client_id(client_id)
        db = SessionLocal()
        try:
            client_record = db.query(Client).filter(Client.client_id == client_id).one()

            # Use the shared mapping utility
            _, _, history = map_client_to_models(client_record)

            SoaServiceBase.log_info(
                f"Credit History retrieved for {client_id}", client_id
            )
            return history

        except NoResultFound:
            SoaServiceBase.log_error(
                f"Client ID not found for credit history: {client_id}", client_id
            )
            raise ClientNotFoundFault(
                detail=f"Client with ID '{client_id}' not found in directory."
            )
        finally:
            db.close()
