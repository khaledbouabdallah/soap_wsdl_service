from loan_solvency_service.shared.minimal_server import start_server

if __name__ == '__main__':
    # This container hosts CreditScoring, SolvencyDecision, and Explanation services
    start_server("SolvencyBusinessLogicServices")