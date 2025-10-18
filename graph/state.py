from typing import TypedDict

class WorkflowState(TypedDict):
    """
    Represents the state of our workflow.
    This object is passed between nodes in the graph.
    """
    case_id: str
    patient_email: str
    decision: str          # 'confirmed' or 'rejected'
    findings: str
    doctor_role: str       # 'junior_doctor' or 'senior_doctor'
    next_step: str         # The result of our routing decision
