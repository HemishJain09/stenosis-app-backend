from datetime import datetime, timedelta
from googleapiclient.discovery import build
from .gcp_auth import get_gcp_credentials
import os
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def create_appointment_event(patient_email: str, title: str = "Follow-up Appointment for Stenosis Review"):
    """
    Creates a new event in Google Calendar for a patient appointment.
    """
    try:
        creds = get_gcp_credentials()
        service = build("calendar", "v3", credentials=creds)

        # Let's schedule the event for 3 days from now at 10 AM
        start_time = (datetime.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        event = {
            "summary": title,
            "description": "This is a follow-up appointment regarding your recent angiography results.",
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "Asia/Kolkata", # Set your local timezone
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "Asia/Kolkata", # Set your local timezone
            },
            "attendees": [
                {"email": patient_email},
                {"email": SENDER_EMAIL}, # Assuming the doctor/clinic is the sender
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        created_event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"✅ Calendar: Successfully created event. Event ID: {created_event.get('htmlLink')}")
        return f"Calendar event created successfully for {patient_email}"
    except Exception as e:
        print(f"❌ Calendar Error: Failed to create event. Error: {e}")
        return f"Error creating calendar event: {e}"
