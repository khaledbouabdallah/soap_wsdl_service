import logging
from zeep import Client
from zeep.exceptions import Fault
import time

logger = logging.getLogger(__name__)


class InternalSoapClient:
    """
    Wrapper for making SOAP calls to internal services with retry logic and metrics.
    """

    def __init__(self, wsdl_url, service_name, max_retries=3, timeout=5):
        """
        Initialize SOAP client for internal service communication.

        :param wsdl_url: Full WSDL URL (e.g., http://crud:8000/CRUDAccess?wsdl)
        :param service_name: Name for logging purposes
        :param max_retries: Number of retry attempts
        :param timeout: Timeout in seconds
        """
        self.wsdl_url = wsdl_url
        self.service_name = service_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.client = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the zeep client with retry logic."""
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Connecting to {self.service_name} at {self.wsdl_url} (attempt {attempt + 1}/{self.max_retries})"
                )
                self.client = Client(self.wsdl_url)
                logger.info(f"Successfully connected to {self.service_name}")
                return
            except Exception as e:
                logger.warning(f"Failed to connect to {self.service_name}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    logger.error(
                        f"Could not connect to {self.service_name} after {self.max_retries} attempts"
                    )
                    raise

    def call_operation(self, operation_name, correlation_id=None, **kwargs):
        """
        Call a SOAP operation with latency tracking.

        :param operation_name: Name of the operation to call
        :param correlation_id: Correlation ID for tracing
        :param kwargs: Operation parameters
        :return: Operation result
        """
        start_time = time.time()

        try:
            logger.info(
                f"[{correlation_id}] Calling {self.service_name}.{operation_name} with params: {kwargs}"
            )

            # Get the operation from the service
            operation = getattr(self.client.service, operation_name)

            # Make the call
            result = operation(**kwargs)

            # Calculate latency
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds

            logger.info(
                f"[{correlation_id}] {self.service_name}.{operation_name} completed in {latency:.2f}ms"
            )

            return result, latency

        except Fault as e:
            latency = (time.time() - start_time) * 1000
            logger.error(
                f"[{correlation_id}] {self.service_name}.{operation_name} failed with SOAP Fault: {e}"
            )
            raise
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(
                f"[{correlation_id}] {self.service_name}.{operation_name} failed: {e}"
            )
            raise
