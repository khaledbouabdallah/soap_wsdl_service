import logging
import uuid
import os
import re
import contextvars
import json

from spyne.application import Application
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.error import Fault
from spyne.model.primitive import Unicode
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.wsgi import WSGIResource
from twisted.internet import endpoints

# Import metrics collector
from loan_solvency_service.shared.metrics import (
    get_metrics_collector,
    get_prometheus_content_type,
)

# Configure logging for the base service
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Context variable for correlation ID (thread-safe)
correlation_id_context = contextvars.ContextVar("correlation_id", default=None)


# --- Custom Faults (Required by 5.1 & 5.2) ---
class ClientNotFoundFault(Fault):
    __namespace__ = "urn:solvency.verification.service:v1"
    __type_name__ = "ClientNotFoundFault"

    detail = Unicode

    def __init__(self, detail=None):
        super(ClientNotFoundFault, self).__init__(
            faultcode="Client.NotFound", faultstring=detail or "Client not found"
        )


class ClientValidationError(Fault):
    __namespace__ = "urn:solvency.verification.service:v1"
    __type_name__ = "ClientValidationError"

    detail = Unicode

    def __init__(self, detail=None):
        super(ClientValidationError, self).__init__(
            faultcode="Client.ValidationError", faultstring=detail or "Validation error"
        )


# --- Helper Functions ---


def generate_correlation_id():
    """Generate a unique correlation ID for request tracing."""
    return str(uuid.uuid4())


def get_correlation_id():
    """Get the current correlation ID from context."""
    cid = correlation_id_context.get()
    if cid is None:
        cid = generate_correlation_id()
        correlation_id_context.set(cid)
    return cid


def set_correlation_id(cid):
    """Set the correlation ID in context."""
    correlation_id_context.set(cid)


def validate_client_id(client_id):
    """
    Validates client ID against the XSD pattern: client-\d{3}
    Raises ClientValidationError if invalid.
    """
    pattern = r"^client-\d{3}$"
    if not re.match(pattern, client_id):
        raise ClientValidationError(
            detail=f"Invalid client ID format: '{client_id}'. "
            f"Expected pattern: client-XXX (where XXX is 3 digits)"
        )


# --- Base Service Class ---


class SoaServiceBase(ServiceBase):
    """
    Abstract base class for all CRUD and Orchestration services.
    Provides utility methods for logging and consistency.
    """

    @staticmethod
    def log_info(message, client_id=None):
        """Log info message with correlation ID and optional client_id tag"""
        cid = get_correlation_id()
        client_tag = f"[{client_id}]" if client_id else ""
        logger.info(f"[{cid}]{client_tag}: {message}")

    @staticmethod
    def log_error(message, client_id=None):
        """Log error message with correlation ID and optional client_id tag"""
        cid = get_correlation_id()
        client_tag = f"[{client_id}]" if client_id else ""
        logger.error(f"[{cid}]{client_tag}: {message}")

    @staticmethod
    def record_metrics(operation_name, latency_ms):
        """Record operation metrics."""
        metrics = get_metrics_collector()
        metrics.record_call(operation_name, latency_ms)


# --- Server Runner Utility ---


def start_spyne_server(
    service_classes, interface_name, port=8000, soap_protocol=Soap11, tns_suffix=""
):
    """
    Configures and starts a Spyne service using the stable Twisted WSGI integration.

    :param service_classes: A list of Spyne ServiceBase classes to expose.
    :param interface_name: A descriptive name for the service interface (used as the URL path).
    """

    # Initialize metrics collector with service name
    get_metrics_collector(interface_name)

    # 3.3: Protocol choice: SOAP 1.1
    # 3.3: Style: document/literal is the default for Spyne's Soap11/12
    application = Application(
        service_classes,
        tns=f"urn:solvency.verification.service:v1{tns_suffix}",
        in_protocol=soap_protocol(validator="lxml"),
        out_protocol=soap_protocol(validator="lxml"),
    )

    wsgi_application = WsgiApplication(application)
    wsgi_app = WSGIResource(reactor, reactor.getThreadPool(), wsgi_application)

    # Root Resource for general serving (including WSDL at ?wsdl)
    root = Resource()
    root.putChild(interface_name.encode("utf-8"), wsgi_app)
    root.putChild(b"health", _HealthResource(interface_name))
    root.putChild(b"metrics", _MetricsResource(interface_name))
    root.putChild(b"prometheus", _PrometheusMetricsResource(interface_name))

    site = Site(root)

    logger.info(f"[{interface_name}] Starting SOAP server on port {port}...")
    logger.info(
        f"[{interface_name}] WSDL available at http://localhost:{port}/{interface_name}?wsdl"
    )
    logger.info(
        f"[{interface_name}] JSON Metrics available at http://localhost:{port}/metrics"
    )
    logger.info(
        f"[{interface_name}] Prometheus Metrics available at http://localhost:{port}/prometheus"
    )

    try:
        endpoint = endpoints.TCP4ServerEndpoint(
            reactor, port, interface=os.getenv("HOST", "0.0.0.0")
        )
        endpoint.listen(site)
        reactor.run()
    except Exception as e:
        logger.error(f"Failed to start reactor: {e}")


# Internal health check
class _HealthResource(Resource):
    """Simple resource to respond to a health check, used by docker-compose."""

    isLeaf = True

    def __init__(self, service_name):
        self.service_name = service_name

    def render_GET(self, request):
        request.setHeader(b"Content-Type", b"text/plain")
        return f"Service {self.service_name} is running and healthy.".encode("utf-8")


# **UPDATED: JSON Metrics endpoint with cache stats**
class _MetricsResource(Resource):
    """Expose QoS metrics in JSON format for monitoring."""

    isLeaf = True

    def __init__(self, service_name):
        self.service_name = service_name

    def render_GET(self, request):
        """Return metrics in JSON format."""
        metrics = get_metrics_collector()

        # **NEW: Try to get cache stats if this is orchestrator**
        cache_stats = None
        if self.service_name == "SolvencyVerification":
            try:
                from loan_solvency_service.services.orchestration.SolvencyVerificationService import (
                    get_cache_instance,
                )

                cache = get_cache_instance()
                cache_stats = cache.get_stats()
            except ImportError:
                pass  # Cache not available on non-orchestrator services

        metrics_data = metrics.get_metrics(cache_stats)
        metrics_data["service_name"] = self.service_name

        request.setHeader(b"Content-Type", b"application/json")
        return json.dumps(metrics_data, indent=2).encode("utf-8")


# Prometheus Metrics endpoint
class _PrometheusMetricsResource(Resource):
    """Expose metrics in Prometheus format for scraping."""

    isLeaf = True

    def __init__(self, service_name):
        self.service_name = service_name

    def render_GET(self, request):
        """Return metrics in Prometheus format."""
        metrics = get_metrics_collector()

        # **NEW: Update cache metrics if available**
        if self.service_name == "SolvencyVerification":
            try:
                from loan_solvency_service.services.orchestration.SolvencyVerificationService import (
                    get_cache_instance,
                )

                cache = get_cache_instance()
                cache_stats = cache.get_stats()
                metrics.update_cache_metrics(cache_stats)
            except ImportError:
                pass

        prometheus_data = metrics.get_prometheus_metrics()

        content_type = get_prometheus_content_type()
        request.setHeader(b"Content-Type", content_type.encode("utf-8"))
        return prometheus_data
