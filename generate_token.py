import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Scopes define permission (Gmail Send + Calendar)
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send"
]

def main():
    creds = None
    # 1. Check if token already exists (and is valid)
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            print("Old token invalid, deleting...")
            os.remove("token.json")
            creds = None

    # 2. If no valid credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                print("Refresh failed, logging in again...")
                creds = None

        if not creds:
            if not os.path.exists("credentials.json"):
                print("❌ Error: 'credentials.json' file not found!")
                print("Please download it from Google Cloud Console and save it in this folder.")
                return

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            # Opens browser for login
            creds = flow.run_local_server(port=0)

        # 3. Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            print("✅ Success! 'token.json' has been generated/updated.")

if __name__ == "__main__":
    main()