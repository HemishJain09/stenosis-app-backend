
from firebase_admin import firestore

def update_case_status_in_db(case_id: str, new_status: str, findings: str = ""):
    """
    Updates the status and findings of a specific case in Firestore.
    """
    try:
        db = firestore.client()
        case_ref = db.collection("cases").document(case_id)
        
        update_data = {"status": new_status}
        if findings:
            update_data["findings"] = findings
            
        case_ref.update(update_data)
        print(f"✅ Firestore: Successfully updated case {case_id} to status {new_status}")
        return f"Successfully updated case {case_id}"
    except Exception as e:
        print(f"❌ Firestore Error: Failed to update case {case_id}. Error: {e}")
        return f"Error updating case: {e}"

def get_patient_email(case_id: str):
    """
    Retrieves the patient's email for a given case ID.
    """
    try:
        db = firestore.client()
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if case_doc.exists:
            return case_doc.to_dict().get("patientEmail")
        else:
            return None
    except Exception as e:
        print(f"❌ Firestore Error: Failed to retrieve patient email for case {case_id}. Error: {e}")
        return None
