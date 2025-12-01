import os
import base64
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

def send_google_email(recipients, subject, body, file_paths=None):
    """
    Sends email via Gmail API.
    """
    try:
        if not os.path.exists(TOKEN_PATH):
            print("Error: token.json missing.")
            return False

        creds = Credentials.from_authorized_user_file(TOKEN_PATH, ["https://www.googleapis.com/auth/gmail.send"])
        service = build("gmail", "v1", credentials=creds)

        message = MIMEMultipart()
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.attach(MIMEText(body, 'html'))

        if file_paths:
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    continue
                
                content_type, encoding = mimetypes.guess_type(file_path)
                if content_type is None or encoding is not None:
                    content_type = 'application/octet-stream'
                main_type, sub_type = content_type.split('/', 1)

                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                part = MIMEBase(main_type, sub_type)
                part.set_payload(file_content)
                encoders.encode_base64(part)
                
                filename = os.path.basename(file_path)
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(part)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"Email Sent! Message Id: {send_message['id']}")
        return True

    except Exception as e:
        print(f"Error sending email: {e}")
        return False