from tools.firestore_tools import get_patient_email, update_case_status_in_db
from tools.gmail_tool import send_notification_email
from tools.calendar_tool import create_appointment_event
from .state import WorkflowState

def start_review_process(state: WorkflowState) -> WorkflowState:
    """
    Initial node: Fetches the patient's email to enrich the state.
    """
    print("--- Starting Review Process ---")
    case_id = state["case_id"]
    patient_email = get_patient_email(case_id)
    if patient_email:
        state["patient_email"] = patient_email
    print(f"State after start: {state}")
    return state

def decide_next_step(state: WorkflowState) -> WorkflowState:
    """
    This is the core routing logic. It inspects the state to decide
    which path the workflow should take next.
    """
    print("--- Deciding Next Step ---")
    doctor_role = state["doctor_role"]
    decision = state["decision"]

    if decision == "rejected":
        # Any rejection, regardless of role, starts the 'close case' process.
        state["next_step"] = "close_case_no_stenosis"
    elif doctor_role == "junior_doctor" and decision == "confirmed":
        state["next_step"] = "escalate_to_senior"
    elif doctor_role == "senior_doctor" and decision == "confirmed":
        state["next_step"] = "notify_and_schedule"
    else:
        state["next_step"] = "end" # Fallback
        
    print(f"Decision: Next step is '{state['next_step']}'")
    return state

def escalate_to_senior(state: WorkflowState):
    """
    Node for junior doctor's confirmation. Updates the case status
    so it appears in the senior doctor's queue.
    """
    print("--- Escalating to Senior Doctor ---")
    case_id = state["case_id"]
    findings = state["findings"]
    update_case_status_in_db(case_id, "pending_senior_review", findings)
    return {"next_step": "end"} # End this workflow run

def close_case_no_stenosis(state: WorkflowState):
    """
    Node for when any doctor rejects a case. Updates status to closed.
    This node now leads to sending a satisfactory email.
    """
    print("--- Closing Case (No Stenosis) ---")
    case_id = state["case_id"]
    findings = state["findings"]
    update_case_status_in_db(case_id, "closed_no_stenosis", findings)
    # The graph will now route to the email node
    return state

def send_satisfactory_email(state: WorkflowState):
    """
    Sends a 'no stenosis found' email to the patient.
    """
    print("--- Sending Satisfactory Email ---")
    patient_email = state["patient_email"]
    case_id = state["case_id"]
    findings = state["findings"]

    email_subject = f"Your Angiography Results for Case ID: {case_id}"
    email_body = f"""
    Dear Patient,

    This email is regarding your recent angiography (Case ID: {case_id}).
    
    A specialist has reviewed your results and found no significant stenosis. 
    
    Doctor's Findings:
    {findings}
    
    If you have any further questions, please contact our clinic.
    
    Sincerely,
    CardioSenseAI Clinic
    """
    send_notification_email(patient_email, email_subject, email_body)
    return {"next_step": "end"}

def notify_and_schedule(state: WorkflowState):
    """
    The final node for a confirmed high-risk case. Updates the DB,
    sends email, and creates a calendar event.
    """
    print("--- Notifying Patient and Scheduling Appointment ---")
    case_id = state["case_id"]
    findings = state["findings"]
    patient_email = state["patient_email"]

    # 1. Update the database
    update_case_status_in_db(case_id, "closed_stenosis_confirmed", findings)

    # 2. Send email notification
    email_subject = "Important: Your Angiography Results and Follow-up Appointment"
    email_body = f"""
    Dear Patient,

    This email is regarding your recent angiography (Case ID: {case_id}).
    
    Based on a review by our senior specialist, a follow-up appointment is recommended. An appointment has been scheduled for you. Please check your Google Calendar for the details.
    
    Doctor's Findings:
    {findings}
    
    Sincerely,
    CardioSenseAI Clinic
    """
    send_notification_email(patient_email, email_subject, email_body)

    # 3. Create calendar event
    create_appointment_event(patient_email)
    
    return {"next_step": "end"}

