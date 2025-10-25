import os
import time
from spyne.decorator import srpc
from zeep.exceptions import Fault as ZeepFault
from loan_solvency_service.shared.base_service import (
    ClientValidationError,
    SoaServiceBase,
    ClientNotFoundFault,
    generate_correlation_id,
    set_correlation_id,
)
from loan_solvency_service.shared.datamodels import (
    ClientId,
    SolvencyReport,
    SolvencyStatus,
)
from loan_solvency_service.shared.soap_client import InternalSoapClient

# **NEW: Import cache module**
from loan_solvency_service.shared.cache import TTLCache

# Get service URLs from environment (with defaults for local development)
CRUD_SERVICE_URL = os.getenv("CRUD_SERVICE_URL", "http://crud:8000/CRUDAccess?wsdl")
BUSINESS_SERVICE_URL = os.getenv(
    "BUSINESS_SERVICE_URL", "http://business:8000/BusinessLogic?wsdl"
)

# **NEW: Cache configuration from environment**
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # Default: 5 minutes
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))  # Default: 1000 entries

# Initialize SOAP clients for internal services (lazy loading)
_crud_client = None
_business_client = None

# **NEW: Initialize cache instance (global, shared across requests)**
_crud_cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS, max_size=CACHE_MAX_SIZE)


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
        _business_client = InternalSoapClient(
            BUSINESS_SERVICE_URL, "BusinessLogicService"
        )
    return _business_client


# **NEW: Helper functions for cached CRUD calls**
def get_client_identity_cached(client_id, correlation_id):
    """
    Get client identity with caching.
    Cache key: identity:{client_id}
    """
    cache_key = f"identity:{client_id}"

    # Try cache first
    cached_value = _crud_cache.get(cache_key)
    if cached_value is not None:
        SoaServiceBase.log_info(f"Cache HIT for {cache_key}", client_id)
        SoaServiceBase.record_metrics(
            "GetClientIdentity_cached", 0
        )  # Zero latency for cache hit
        return cached_value, 0

    # Cache miss - call CRUD service
    SoaServiceBase.log_info(f"Cache MISS for {cache_key}", client_id)
    crud_client = get_crud_client()
    result, latency = crud_client.call_operation(
        "GetClientIdentity", correlation_id=correlation_id, client_id=client_id
    )

    # Store in cache
    _crud_cache.put(cache_key, result)
    return result, latency


def get_client_financials_cached(client_id, correlation_id):
    """
    Get client financials with caching.
    Cache key: financials:{client_id}
    """
    cache_key = f"financials:{client_id}"

    # Try cache first
    cached_value = _crud_cache.get(cache_key)
    if cached_value is not None:
        SoaServiceBase.log_info(f"Cache HIT for {cache_key}", client_id)
        SoaServiceBase.record_metrics("GetClientFinancials_cached", 0)
        return cached_value, 0

    # Cache miss - call CRUD service
    SoaServiceBase.log_info(f"Cache MISS for {cache_key}", client_id)
    crud_client = get_crud_client()
    result, latency = crud_client.call_operation(
        "GetClientFinancials", correlation_id=correlation_id, client_id=client_id
    )

    # Store in cache
    _crud_cache.put(cache_key, result)
    return result, latency


def get_client_credit_history_cached(client_id, correlation_id):
    """
    Get client credit history with caching.
    Cache key: history:{client_id}
    """
    cache_key = f"history:{client_id}"

    # Try cache first
    cached_value = _crud_cache.get(cache_key)
    if cached_value is not None:
        SoaServiceBase.log_info(f"Cache HIT for {cache_key}", client_id)
        SoaServiceBase.record_metrics("GetClientCreditHistory_cached", 0)
        return cached_value, 0

    # Cache miss - call CRUD service
    SoaServiceBase.log_info(f"Cache MISS for {cache_key}", client_id)
    crud_client = get_crud_client()
    result, latency = crud_client.call_operation(
        "GetClientCreditHistory", correlation_id=correlation_id, client_id=client_id
    )

    # Store in cache
    _crud_cache.put(cache_key, result)
    return result, latency


class SolvencyVerificationService(SoaServiceBase):
    """
    2.3: SolvencyVerificationService - Main orchestration service.
    Coordinates all CRUD and business logic services via SOAP calls to produce a complete SolvencyReport.
    **ENHANCED: Now uses TTL-based caching for CRUD operations.**
    """

    @srpc(
        ClientId,
        _returns=SolvencyReport,
        _faults=[ClientNotFoundFault, ClientValidationError],
    )
    def VerifySolvency(client_id):
        """
        VerifySolvency(clientId) -> SolvencyReport

        Main entry point: orchestrates all services to verify client solvency.
        **Uses caching for CRUD calls to improve performance.**
        """

        # Generate correlation ID for this request
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        # Track overall operation time
        operation_start = time.time()

        SoaServiceBase.log_info(
            f"Starting solvency verification for client_id={client_id}", client_id
        )

        try:
            business_client = get_business_client()

            # **CHANGED: STEP 1 - Use cached CRUD calls**
            SoaServiceBase.log_info("Fetching client data (with caching)", client_id)

            # Call with cache
            client_identity, latency1 = get_client_identity_cached(
                client_id, correlation_id
            )
            if latency1 > 0:  # Only record if not from cache
                SoaServiceBase.record_metrics("GetClientIdentity", latency1)

            financials, latency2 = get_client_financials_cached(
                client_id, correlation_id
            )
            if latency2 > 0:
                SoaServiceBase.record_metrics("GetClientFinancials", latency2)

            credit_history, latency3 = get_client_credit_history_cached(
                client_id, correlation_id
            )
            if latency3 > 0:
                SoaServiceBase.record_metrics("GetClientCreditHistory", latency3)

            # **UNCHANGED: STEP 2 - Compute credit score (no caching for business logic)**
            SoaServiceBase.log_info("Computing credit score", client_id)

            credit_score, latency4 = business_client.call_operation(
                "ComputeCreditScore",
                correlation_id=correlation_id,
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy,
            )
            SoaServiceBase.record_metrics("ComputeCreditScore", latency4)

            # **UNCHANGED: STEP 3 - Make solvency decision**
            SoaServiceBase.log_info("Making solvency decision", client_id)

            solvency_status_response, latency5 = business_client.call_operation(
                "DecideSolvency",
                correlation_id=correlation_id,
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                credit_score=credit_score,
            )
            SoaServiceBase.record_metrics("DecideSolvency", latency5)

            # Handle SOAP response
            if isinstance(solvency_status_response, str):
                status_value = solvency_status_response
            elif hasattr(solvency_status_response, "status"):
                status_value = solvency_status_response.status
            else:
                status_value = str(solvency_status_response)

            solvency_status = SolvencyStatus(status=status_value)

            # **UNCHANGED: STEP 4 - Generate explanations**
            SoaServiceBase.log_info("Generating explanations", client_id)

            explanations, latency6 = business_client.call_operation(
                "Explain",
                correlation_id=correlation_id,
                credit_score=credit_score,
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy,
            )
            SoaServiceBase.record_metrics("Explain", latency6)

            # **UNCHANGED: STEP 5 - Assemble final report**
            report = SolvencyReport(
                client_identity=client_identity,
                financials=financials,
                credit_history=credit_history,
                credit_score=credit_score,
                solvency_status=solvency_status,
                explanations=explanations,
            )

            # Calculate total operation time
            total_latency = (time.time() - operation_start) * 1000
            SoaServiceBase.record_metrics("VerifySolvency", total_latency)

            # **NEW: Log cache statistics**
            cache_stats = _crud_cache.get_stats()
            SoaServiceBase.log_info(
                f"Solvency verification completed: {status_value} "
                f"(total: {total_latency:.2f}ms, cache hit rate: {cache_stats['hit_rate_percent']}%)",
                client_id,
            )

            return report

        except ZeepFault as e:
            # Handle SOAP faults from internal services and propagate them
            SoaServiceBase.log_error(
                f"SOAP Fault from internal service: {e}", client_id
            )

            fault_code = str(e.code) if e.code else ""
            fault_message = str(e.message) if e.message else str(e)

            if "NotFound" in fault_code or "not found" in fault_message.lower():
                raise ClientNotFoundFault(detail=fault_message)
            elif (
                "ValidationError" in fault_code or "validation" in fault_message.lower()
            ):
                raise ClientValidationError(detail=fault_message)
            else:
                SoaServiceBase.log_error(
                    f"Unknown SOAP fault: code={fault_code}, message={fault_message}",
                    client_id,
                )
                raise

        except ClientNotFoundFault:
            SoaServiceBase.log_error("Client not found during verification", client_id)
            raise
        except ClientValidationError:
            SoaServiceBase.log_error("Validation error during verification", client_id)
            raise
        except Exception as e:
            SoaServiceBase.log_error(
                f"Unexpected error during verification: {e}", client_id
            )
            raise


# **NEW: Helper to get cache instance (for metrics endpoint)**
def get_cache_instance():
    """Get the global cache instance for metrics reporting."""
    return _crud_cache
