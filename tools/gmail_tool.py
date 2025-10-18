import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from .gcp_auth import get_gcp_credentials

def send_notification_email(recipient_email: str, subject: str, body: str):
    """
    Sends an email notification using the Gmail API.
    """
    try:
        creds = get_gcp_credentials()
        service = build("gmail", "v1", credentials=creds)
        
        message = EmailMessage()
        message.set_content(body)
        message["To"] = recipient_email
        message["Subject"] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        create_message_request = {"raw": encoded_message}
        
        send_message = (
            service.users().messages().send(userId="me", body=create_message_request).execute()
        )
        print(f"✅ Gmail: Successfully sent email to {recipient_email}. Message ID: {send_message['id']}")
        return f"Email sent successfully to {recipient_email}"
    except Exception as e:
        print(f"❌ Gmail Error: Failed to send email. Error: {e}")
        return f"Error sending email: {e}"
