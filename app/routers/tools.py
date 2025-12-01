import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import List
from app.celery_worker import schedule_meeting_task, send_email_task

router = APIRouter()

# --- Meeting Scheduler Endpoint ---
class MeetingRequest(BaseModel):
    summary: str
    start_time: str 
    end_time: str
    emails: list[str]

@router.post("/schedule-meeting")
async def schedule_meeting(data: MeetingRequest):
    # Push to Celery Queue
    task = schedule_meeting_task.delay(
        data.summary, data.start_time, data.end_time, data.emails
    )
    return {"message": "Scheduling in background...", "task_id": task.id}


# --- Email Sender Endpoint ---
@router.post("/send-email")
async def send_email(
    recipients: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    files: List[UploadFile] = File(None)
):
    # Convert comma-separated string to list
    recipient_list = [email.strip() for email in recipients.split(",")]
    file_paths = []

    # 1. Save uploaded files temporarily (Celery needs paths)
    if files:
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        for file in files:
            # Check if filename exists to avoid error
            if file.filename:
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                file_paths.append(file_path)

    # 2. Push task to Celery
    task = send_email_task.delay(recipient_list, subject, body, file_paths)
    
    return {"message": "Email sending started...", "task_id": task.id}