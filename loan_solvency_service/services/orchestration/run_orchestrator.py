# The actual Spyne/SOAP service implementation will go in 
# SolvencyVerificationService.py, but for now, we just start the server.

from loan_solvency_service.shared.minimal_server import start_server

# In the final implementation, this service will also serve the WSDL 
# and SOAP endpoint.
if __name__ == '__main__':
    start_server("SolvencyOrchestrator")