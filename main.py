import os
import uuid
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, ConfigDict
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from typing import List, Optional
import logging

# --- LangGraph Integration ---
from graph.workflow import app as stenosis_workflow_app

# --- GCP Tools ---
from tools.gcp_auth import get_gcp_credentials

# Load environment variables from .env file
load_dotenv()

# --- Firebase Initialization ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- FastAPI App Initialization ---
app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AI Model Simulation ---
def simulate_ai_model(filename: str):
    """
    This function simulates a pre-trained model analyzing an angiography video.
    """
    print(f"--- Simulating AI analysis for file: {filename} ---")
    risk_level = random.choice(['high', 'low', 'low'])
    if risk_level == 'high':
        confidence = random.randint(80, 95)
        report_text = f"Model analysis indicates a high probability ({confidence}%) of significant stenosis. Immediate review by a senior specialist is recommended."
    else:
        confidence = random.randint(60, 79)
        report_text = f"Model analysis indicates a low to moderate probability ({confidence}%) of stenosis. A routine check by a junior doctor is advised."
    print(f"--- Simulation Result: Risk Level='{risk_level}' ---")
    return {"riskLevel": risk_level, "modelReport": report_text}

# --- Security ---
async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        user_doc = db.collection('users').document(decoded_token['uid']).get()
        if user_doc.exists:
            return {**decoded_token, **user_doc.to_dict()}
        raise HTTPException(status_code=404, detail="User not found in Firestore.")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# --- Pydantic Models ---
class UserRegister(BaseModel):
    uid: str
    name: str
    email: EmailStr
    role: str

class Patient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    uid: str
    name: str
    email: str

class CaseReview(BaseModel):
    decision: str
    findings: str

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Stenosis App Backend is running!"}

@app.post("/register")
async def register_user(user: UserRegister):
    try:
        user_ref = db.collection('users').document(user.uid)
        user_ref.set({'name': user.name, 'email': user.email, 'role': user.role})
        return {"message": "User registered successfully in Firestore."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patients")
async def get_patients(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'clinic':
        raise HTTPException(status_code=403, detail="Only clinic personnel can access this.")
    try:
        patients_ref = db.collection('users').where('role', '==', 'patient').stream()
        patient_list = []
        for doc in patients_ref:
            doc_data = doc.to_dict()
            if 'name' in doc_data and 'email' in doc_data:
                patient_list.append({"uid": doc.id, **doc_data})
            else:
                print(f"⚠️ WARNING: Skipping document {doc.id} due to missing 'name' or 'email' field.")
        return patient_list
    except Exception as e:
        logging.error(f"Error fetching patients: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching patients.")

@app.post("/cases")
async def create_case(
    patientName: str = Form(...),
    patientEmail: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get('role') != 'clinic':
        raise HTTPException(status_code=403, detail="Only clinic personnel can perform this action.")
    try:
        simulation_result = simulate_ai_model(file.filename)
        risk_level = simulation_result["riskLevel"]
        model_report = simulation_result["modelReport"]
        
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET environment variable not set.")
        
        bucket = storage.bucket(bucket_name)
        unique_filename = f"{uuid.uuid4()}-{file.filename}"
        blob = bucket.blob(f"dicom_files/{unique_filename}")
        
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()
        
        status = "pending_senior_review" if risk_level == "high" else "pending_junior_review"
        
        case_data = {
            "patientName": patientName,
            "patientEmail": patientEmail,
            "dicomFileUrl": blob.public_url,
            "status": status,
            "modelReport": model_report,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        db.collection("cases").add(case_data)
        return {"message": "Case created and sent for analysis successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")

@app.get("/cases")
async def get_cases(current_user: dict = Depends(get_current_user)):
    role = current_user.get('role')
    if role not in ['junior_doctor', 'senior_doctor']:
        raise HTTPException(status_code=403, detail="Access denied.")
    status_to_fetch = "pending_junior_review" if role == 'junior_doctor' else "pending_senior_review"
    cases_ref = db.collection('cases').where('status', '==', status_to_fetch).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in cases_ref]

@app.put("/cases/{case_id}/review")
async def review_case(case_id: str, review: CaseReview, current_user: dict = Depends(get_current_user)):
    doctor_role = current_user.get('role')
    if doctor_role not in ['junior_doctor', 'senior_doctor']:
        raise HTTPException(status_code=403, detail="Only doctors can review cases.")
    try:
        initial_state = {
            "case_id": case_id,
            "decision": review.decision,
            "findings": review.findings,
            "doctor_role": doctor_role,
        }
        print(f"--- Invoking LangGraph workflow with initial state: {initial_state} ---")
        stenosis_workflow_app.invoke(initial_state)
        return {"message": "Case review process has been initiated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start review workflow: {str(e)}")

@app.get("/init-gcp")
async def init_gcp_auth():
    print("--- Attempting to initialize GCP credentials... ---")
    try:
        get_gcp_credentials()
        return {"message": "GCP credentials initialized or already exist."}
    except Exception as e:
        return {"message": f"An error occurred: {e}"}

