from loan_solvency_service.shared.minimal_server import start_server

if __name__ == '__main__':
    # This container hosts ClientDirectory, FinancialData, and CreditBureau services
    start_server("SolvencyCRUDServices")