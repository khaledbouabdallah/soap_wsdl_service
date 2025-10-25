import logging
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

# Configure basic logging once
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Simple Resource to respond to a health check
class HealthResource(Resource):
    isLeaf = True

    def __init__(self, service_name):
        self.service_name = service_name

    def render_GET(self, request):
        # A simple response indicating the service is alive
        request.setHeader(b"Content-Type", b"text/plain")
        return f"{self.service_name} is running and healthy.".encode("utf-8")


def start_server(service_name, port=8000):
    """Starts a minimal Twisted HTTP server for a given service."""

    root = Resource()
    root.putChild(b"health", HealthResource(service_name))

    # Use the logger instead of print
    logger.info(f"[{service_name}] Starting server on port {port}...")

    factory = Site(root)
    reactor.listenTCP(port, factory)

    reactor.run()
    # Use the logger instead of print
    logger.info(f"[{service_name}] Server stopped.")


if __name__ == "__main__":
    logger.warning("This module is a utility and should be imported.")
