import logging
import uuid
import os

from spyne.application import Application
# CRITICAL FIX: Use the standard WSGI application adapter for stability
from spyne.server.wsgi import WsgiApplication 
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.error import Fault
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.resource import Resource
# We use Twisted's generic WSGI resource adapter
from twisted.web.wsgi import WSGIResource 
from twisted.internet import endpoints

# Configure logging for the base service
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Custom Faults (Required by 5.1 & 5.2) ---

class ClientNotFoundFault(Fault):
    """5.1: SOAP Fault Client.NotFound"""
    __faultcode__ = 'Client.NotFound'

class ClientValidationError(Fault):
    """5.2: SOAP Fault Client.ValidationError (for code-level semantic checks)"""
    __faultcode__ = 'Client.ValidationError'

# --- Base Service Class ---

class SoaServiceBase(ServiceBase):
    """
    Abstract base class for all CRUD and Orchestration services.
    Provides utility methods for logging and consistency.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Note: Correlation ID is usually generated per request, but this 
        # is a placeholder for the service instance itself.
        self.correlation_id = str(uuid.uuid4())
        self.service_name = self.__class__.__name__

    # Utility method for correlation logging
    def log_info(self, message, client_id=None):
        cid_tag = f"[{client_id}]" if client_id else ""
        logger.info(f"[CID:{self.correlation_id}] {self.service_name} {cid_tag}: {message}")

    # Utility method for correlation logging
    def log_error(self, message, client_id=None):
        cid_tag = f"[{client_id}]" if client_id else ""
        logger.error(f"[CID:{self.correlation_id}] {self.service_name} {cid_tag}: {message}")

# --- Server Runner Utility (FIXED) ---

def start_spyne_server(service_classes, interface_name, port=8000, soap_protocol=Soap11, tns_suffix=""):
    """
    Configures and starts a Spyne service using the stable Twisted WSGI integration.
    
    :param service_classes: A list of Spyne ServiceBase classes to expose.
    :param interface_name: A descriptive name for the service interface (used as the URL path).
    """
    
    # 3.3: Protocol choice: SOAP 1.1
    # 3.3: Style: document/literal is the default for Spyne's Soap11/12
    application = Application(
        service_classes, # Takes a list of service classes
        tns=f'urn:solvency.verification.service:v1{tns_suffix}',
        in_protocol=soap_protocol(validator='lxml'),
        out_protocol=soap_protocol(validator='lxml'), 
    )
    
    # Wrap the Spyne Application in Twisted's WSGIResource
    # This completely avoids the internal Spyne/Twisted module clash
    wsgi_app = WSGIResource(reactor, reactor.getThreadPool(), application)
    
    # Root Resource for general serving (including WSDL at ?wsdl)
    root = Resource()
    # The SOAP endpoint will be available at /interface_name
    root.putChild(interface_name.encode('utf-8'), wsgi_app)
    root.putChild(b"health", _HealthResource(interface_name)) # Keep the health check
    
    # We must wrap the WSGIResource in a Site to manage the HTTP requests
    site = Site(root)
    
    logger.info(f"[{interface_name}] Starting SOAP server on port {port}...")
    logger.info(f"[{interface_name}] WSDL available at http://localhost:{port}/{interface_name}?wsdl")
    
    # Use endpoints for modern Twisted TCP listening
    try:
        endpoint = endpoints.TCP4ServerEndpoint(reactor, port, interface=os.getenv("HOST", "0.0.0.0"))
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
        return f"Service {self.service_name} is running and healthy.".encode('utf-8')