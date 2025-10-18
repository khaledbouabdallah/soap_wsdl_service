from spyne.decorator import srpc
from loan_solvency_service.shared.base_service import SoaServiceBase, ClientNotFoundFault
from loan_solvency_service.shared.datamodels import ClientId, SolvencyReport

# Import CRUD services
from loan_solvency_service.services.crud.ClientDirectoryService import ClientDirectoryService
from loan_solvency_service.services.crud.FinancialDataService import FinancialDataService
from loan_solvency_service.services.crud.CreditBureauService import CreditBureauService

# Import Business Logic services
from loan_solvency_service.services.business_logic.CreditScoringService import CreditScoringService
from loan_solvency_service.services.business_logic.SolvencyDecisionService import SolvencyDecisionService
from loan_solvency_service.services.business_logic.ExplanationService import ExplanationService

class SolvencyVerificationService(SoaServiceBase):
    """
    2.3: SolvencyVerificationService - Main orchestration service.
    Coordinates all CRUD and business logic services to produce a complete SolvencyReport.
    """
    
    @srpc(ClientId, _returns=SolvencyReport)
    def VerifySolvency(client_id):
        """
        VerifySolvency(clientId) -> SolvencyReport
        
        Main entry point: orchestrates all services to verify client solvency.
        """
        
        SoaServiceBase.log_info(f"Starting solvency verification", client_id)
        
        try:
            # STEP 1: Retrieve client data from CRUD services
            SoaServiceBase.log_info("Fetching client data from CRUD services", client_id)
            
            client_identity = ClientDirectoryService.GetClientIdentity(client_id)
            financials = FinancialDataService.GetClientFinancials(client_id)
            credit_history = CreditBureauService.GetClientCreditHistory(client_id)
            
            # STEP 2: Compute credit score
            SoaServiceBase.log_info("Computing credit score", client_id)
            
            credit_score = CreditScoringService.ComputeCreditScore(
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy
            )
            
            # STEP 3: Make solvency decision
            SoaServiceBase.log_info("Making solvency decision", client_id)
            
            solvency_status = SolvencyDecisionService.DecideSolvency(
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                credit_score=credit_score
            )
            
            # STEP 4: Generate explanations
            SoaServiceBase.log_info("Generating explanations", client_id)
            
            explanations = ExplanationService.Explain(
                credit_score=credit_score,
                monthly_income=financials.monthly_income,
                monthly_expenses=financials.monthly_expenses,
                debt=credit_history.debt,
                late_payments=credit_history.late_payments,
                has_bankruptcy=credit_history.has_bankruptcy
            )
            
            # STEP 5: Assemble the final report
            report = SolvencyReport(
                client_identity=client_identity,
                financials=financials,
                credit_history=credit_history,
                credit_score=credit_score,
                solvency_status=solvency_status,
                explanations=explanations
            )
            
            SoaServiceBase.log_info(
                f"Solvency verification completed: {solvency_status.status}", 
                client_id
            )
            
            return report
            
        except ClientNotFoundFault:
            # Re-raise the fault from CRUD services
            SoaServiceBase.log_error(f"Client not found during verification", client_id)
            raise
        except Exception as e:
            # Log unexpected errors
            SoaServiceBase.log_error(f"Unexpected error during verification: {e}", client_id)
            raise