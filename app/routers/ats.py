import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Application, User
from app.routers.auth import get_current_user  
from app.celery_worker import scan_resume_task
from pydantic import BaseModel

router = APIRouter()

# --- Pydantic Schemas (Validation) ---
class JobCreate(BaseModel):
    title: str
    description: str
    location: str

class JobResponse(JobCreate):
    id: int
    company_id: int
    status: str


# 1. CREATE JOB POSTING (HR Only)

@router.post("/jobs", response_model=JobResponse)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
   
    # 1. Check if user belongs to a company
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User is not linked to any company")

    # 2. Save Job to DB
    new_job = Job(
        title=job_data.title,
        description=job_data.description, # 🔥 AI isko use karega
        location=job_data.location,
        company_id=current_user.company_id,
        status="Open"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return new_job


# 2. VIEW ALL JOBS (Company Specific)

@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Logged in user ki company ke saare jobs dikhata hai"""
    return db.query(Job).filter(Job.company_id == current_user.company_id).all()

# 3. APPLY / UPLOAD RESUME (Trigger AI)

@router.post("/jobs/{job_id}/apply")
async def upload_resume(
    job_id: int,
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
   
    # Verify Job Exists & Belongs to User's Company
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 1. Save File Temporarily
    upload_dir = "temp_resumes"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Unique filename to avoid collision
    safe_filename = f"{job_id}_{candidate_email}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Create Application Entry in DB (Initial Status: Pending)
    application = Application(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_id=job.id,
        status="Scanning...", # ON UI USER SEE "Scanning..."
        match_score=0.0
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # 3.  Trigger AI Celery Task
  
    task = scan_resume_task.delay(application.id, file_path)

    return {
        "message": "Resume uploaded. AI analysis started.",
        "application_id": application.id,
        "task_id": task.id
    }


# 4. VIEW APPLICANTS (With AI Scores)

@router.get("/jobs/{job_id}/applicants")
def get_applicants(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns list of candidates sorted by AI Match Score (Highest first)
    """
    # Security check
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applicants = db.query(Application)\
        .filter(Application.job_id == job_id)\
        .order_by(Application.match_score.desc())\
        .all()
        
    return applicants