import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, User
from app.routers.auth import get_current_user
from app.celery_worker import process_document_task
from pydantic import BaseModel

router = APIRouter()

# --- Pydantic Schema ---
class DocumentResponse(BaseModel):
    id: int
    filename: str
    company_id: int
    
    class Config:
        from_attributes = True


# 1. UPLOAD POLICY DOCUMENTS (Triggers RAG)
@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    1. HR uploads PDF/DOCX policies.
    2. Files saved temporarily.
    3. DB entry created.
    4. Celery triggers 'process_document_task' (Chunking + Embedding).
    """
    # Security Check
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User is not linked to any company")

    # Temp directory for processing
    upload_dir = "temp_documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded_tasks = []

    for file in files:
        # 1. Save file to disk
        # Filename ko unique banane ki zaroorat nahi kyunki DB ID unique hai,
        # lekin collision avoid karne ke liye prefix lagate hain.
        safe_filename = f"{current_user.company_id}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Create DB Entry (Initial Status placeholder)
        new_doc = Document(
            filename=file.filename,
            content="Processing...", # Celery will update this with real text
            company_id=current_user.company_id
            
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # 3.  Trigger Celery Task
        task = process_document_task.delay(new_doc.id, file_path)
        
        uploaded_tasks.append({
            "filename": file.filename,
            "doc_id": new_doc.id,
            "task_id": task.id
        })

    return {
        "message": f"Uploading {len(files)} documents for processing.",
        "tasks": uploaded_tasks
    }

# 2. LIST COMPANY DOCUMENTS
@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns list of documents uploaded by THIS user's company only.
    """
    docs = db.query(Document).filter(Document.company_id == current_user.company_id).all()
    return docs