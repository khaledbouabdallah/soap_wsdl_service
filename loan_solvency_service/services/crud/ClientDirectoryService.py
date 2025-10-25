from spyne.decorator import srpc
from loan_solvency_service.shared.base_service import (
    SoaServiceBase,
    ClientNotFoundFault,
    ClientValidationError,
    validate_client_id,
)
from loan_solvency_service.shared.datamodels import (
    ClientId,
    ClientIdentity,
    map_client_to_models,
)
from loan_solvency_service.shared.db_setup import SessionLocal, Client
from sqlalchemy.orm.exc import NoResultFound


class ClientDirectoryService(SoaServiceBase):
    """
    2.1: ClientDirectoryService - Retrieves client identity information.
    """

    @srpc(
        ClientId,
        _returns=ClientIdentity,
        _faults=[ClientNotFoundFault, ClientValidationError],
    )
    def GetClientIdentity(client_id):
        """GetClientIdentity(clientId) -> {name, address}"""

        validate_client_id(client_id)
        # Use a new session per request (best practice for threading/request lifecycle)
        db = SessionLocal()

        # Use client_id argument directly (Spyne handles XSD validation already)
        try:
            # SQLAlchemy query to find the client
            client_record = db.query(Client).filter(Client.client_id == client_id).one()

            # Use the shared mapping utility
            identity, _, _ = map_client_to_models(client_record)

            SoaServiceBase.log_info(f"Identity retrieved for {client_id}", client_id)
            return identity

        except NoResultFound:
            SoaServiceBase.log_error(f"Client ID not found: {client_id}", client_id)
            # 5.1: Raise SOAP Fault Client.NotFound
            raise ClientNotFoundFault(
                detail=f"Client with ID '{client_id}' not found in directory."
            )
        finally:
            db.close()
