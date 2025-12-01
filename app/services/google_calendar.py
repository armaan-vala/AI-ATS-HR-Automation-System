import os
import uuid
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Root folder se token path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

def create_meeting_event(summary, start_time_str, end_time_str, attendees_emails, description="Meeting created by AIONE"):
    """
    Creates a Google Calendar event.
    """
    if not os.path.exists(TOKEN_PATH):
        print("Error: token.json not found! Please authorize Google Account first.")
        return "Error: Google Token Missing"

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, ["https://www.googleapis.com/auth/calendar"])
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time_str, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time_str, "timeZone": "Asia/Kolkata"},
            "attendees": [{"email": email} for email in attendees_emails],
            "conferenceData": {
                "createRequest": {
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    "requestId": str(uuid.uuid4())
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 30},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        event_result = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute()

        meet_link = event_result.get("hangoutLink", "No Meet link created")
        return meet_link

    except Exception as e:
        print(f"Google Calendar Error: {e}")
        return f"Failed to schedule: {str(e)}"