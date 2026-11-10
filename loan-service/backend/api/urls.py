from django.urls import path
from .views import (
    get_completed_loans_view,
    get_pending_loans_view,
    get_loan_details_view,
    update_loan_view,
    StartLoanWorkflowView,  
    CheckLoanWorkflowStatusView,
    MonitorLoanStatusView,  
    UpdateClientChoiceView,
    MonitorFinalDecisionView, 
)

urlpatterns = [
    path("completed-loans/", get_completed_loans_view, name="completed-loans"),  
    path("pending-loans/", get_pending_loans_view, name="pending-loans"),  
    path("loans/<str:email>/<str:timestamp>/", get_loan_details_view, name="loan-details"),
    path("loans/<str:email>/<str:timestamp>/update/", update_loan_view, name="update-loan"),
    path("start-loan-workflow/", StartLoanWorkflowView.as_view(), name="start-loan-workflow"),  
    path("check-loan-workflow-status/", CheckLoanWorkflowStatusView.as_view(), name="check-loan-workflow-status"),
    path("monitor-loan-status/", MonitorLoanStatusView.as_view(), name="monitor-loan-status"),  # Endpoint para monitorar status
    path("update-client-choice/", UpdateClientChoiceView.as_view(), name="update-client-choice"),  # Endpoint para atualizar escolha
    path("monitor-final-decision/", MonitorFinalDecisionView.as_view(), name="monitor-final-decision"),
]
