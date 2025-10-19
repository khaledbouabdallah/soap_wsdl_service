import os
import time
from spyne.decorator import srpc
from zeep.exceptions import Fault as ZeepFault
from loan_solvency_service.shared.base_service import (
    ClientValidationError, SoaServiceBase, ClientNotFoundFault,
    generate_correlation_id, set_correlation_id, get_correlation_id
)
from loan_solvency_service.shared.datamodels import ClientId, SolvencyReport, SolvencyStatus
from loan_solvency_service.shared.soap_client import InternalSoapClient

# Get service URLs from environment (with defaults for local development)
CRUD_SERVICE_URL = os.getenv("CRUD_SERVICE_URL", "http://crud:8000/CRUDAccess?wsdl")
BUSINESS_SERVICE_URL = os.getenv("BUSINESS_SERVICE_URL", "http://business:8000/BusinessLogic?wsdl")

# Initialize SOAP clients for internal services (lazy loading)
_crud_client = None
_business_client = None

def get_crud_client():
    """Get or create CRUD service client."""
    global _crud_client
    if _crud_client is None:
        _crud_client = InternalSoapClient(CRUD_SERVICE_URL, "CRUDService")
    return _crud_client

def get_business_client():
    """Get or create Business Logic service client."""
    global _business_client
    if _business_client is None:
        _business_client = InternalSoapClient(BUSINESS_SERVICE_URL, "BusinessLogicService")
    return _business_client


class SolvencyVerificationService(SoaServiceBase):
    """
    2.3: SolvencyVerificationService - Main orchestration service.
    Coordinates all CRUD and business logic services via SOAP calls to produce a complete SolvencyReport.
    """
    
    @srpc(ClientId, _returns=SolvencyReport, _faults=[ClientNotFoundFault, ClientValidationError])
    def VerifySolvency(client_id):
        """
        VerifySolvency(clientId) -> SolvencyReport
        
        Main entry point: orchestrates all services to verify client solvency.
        """
        
        # Generate correlation ID for this request
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        
        # Track overall operation time
        operation_start = time.time()
        
        SoaServiceBase.log_info(f"Starting solvency verification for client_id={client_id}", client_id)
        
        try:
            crud_client = get_crud_client()
            business_client = get_business_client()
            
            # STEP 1: Retrieve client data from CRUD services via SOAP
            SoaServiceBase.log_info("Fetching client data from CRUD services", client_id)
            
            # Call GetClientIdentity
            client_identity, latency1 = crud_client.call_operation(
                "GetClientIdentity",
                correlation_id=correlation_id,
                client_id=client_id
            )
            SoaServiceBase.record_metrics("GetClientIdentity", latency1)
            
            # Call GetClientFinancials
            financials, latency2 = crud_client.call_operation(
                "GetClientFinancials",
                correlation_id=correlation_id,
                client_id=client_id
            )
            SoaServiceBase.record_metrics("GetClientFinancials", latency2)
            
            # Call GetClientCreditHistory
            credit_history, latency3 = crud_client.call_operation(
                "GetClientCreditHistory",
                correlation_id=correlation_id,
                client_id=client_id
            )
            SoaServiceBase.record_metrics("GetClientCreditHistory", latency3)
            
            # STEP 2: Compute credit score via SOAP
            SoaServiceBase.log_info("Computing credit score", client_id)
            
            credit_score, latency4 = business_client.call_operation(
                "ComputeCreditScore",
                correlation_id=correlation_id,
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy
            )
            SoaServiceBase.record_metrics("ComputeCreditScore", latency4)
            
            # STEP 3: Make solvency decision via SOAP
            SoaServiceBase.log_info("Making solvency decision", client_id)
            
            solvency_status_response, latency5 = business_client.call_operation(
                "DecideSolvency",
                correlation_id=correlation_id,
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                credit_score=credit_score
            )
            SoaServiceBase.record_metrics("DecideSolvency", latency5)
            
            # Handle SOAP response: zeep returns the status as a string or object with .status
            if isinstance(solvency_status_response, str):
                # Direct string from SOAP
                status_value = solvency_status_response
            elif hasattr(solvency_status_response, 'status'):
                # ComplexModel with .status attribute
                status_value = solvency_status_response.status
            else:
                # Fallback
                status_value = str(solvency_status_response)
            
            # Create the SolvencyStatus object for the report
            solvency_status = SolvencyStatus(status=status_value)
            
            # STEP 4: Generate explanations via SOAP
            SoaServiceBase.log_info("Generating explanations", client_id)
            
            explanations, latency6 = business_client.call_operation(
                "Explain",
                correlation_id=correlation_id,
                credit_score=credit_score,
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy
            )
            SoaServiceBase.record_metrics("Explain", latency6)
            
            # STEP 5: Assemble the final report
            report = SolvencyReport(
                client_identity=client_identity,
                financials=financials,
                credit_history=credit_history,
                credit_score=credit_score,
                solvency_status=solvency_status,
                explanations=explanations
            )
            
            # Calculate total operation time
            total_latency = (time.time() - operation_start) * 1000
            SoaServiceBase.record_metrics("VerifySolvency", total_latency)
            
            SoaServiceBase.log_info(
                f"Solvency verification completed: {status_value} (total time: {total_latency:.2f}ms)", 
                client_id
            )
            
            return report
            
        except ZeepFault as e:
            # Handle SOAP faults from internal services and propagate them
            SoaServiceBase.log_error(f"SOAP Fault from internal service: {e}", client_id)
            
            # Check fault code and re-raise appropriate Spyne fault
            fault_code = str(e.code) if e.code else ""
            fault_message = str(e.message) if e.message else str(e)
            
            if "NotFound" in fault_code or "not found" in fault_message.lower():
                raise ClientNotFoundFault(detail=fault_message)
            elif "ValidationError" in fault_code or "validation" in fault_message.lower():
                raise ClientValidationError(detail=fault_message)
            else:
                # Unknown SOAP fault, log and re-raise as generic error
                SoaServiceBase.log_error(f"Unknown SOAP fault: code={fault_code}, message={fault_message}", client_id)
                raise
            
        except ClientNotFoundFault:
            # Re-raise the fault from CRUD services (direct Python calls or already converted)
            SoaServiceBase.log_error("Client not found during verification", client_id)
            raise
        except ClientValidationError:
            # Re-raise validation errors (direct Python calls or already converted)
            SoaServiceBase.log_error("Validation error during verification", client_id)
            raise
        except Exception as e:
            # Log unexpected errors
            SoaServiceBase.log_error(f"Unexpected error during verification: {e}", client_id)
            raise