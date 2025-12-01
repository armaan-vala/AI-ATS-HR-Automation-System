import os
from celery import Celery
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Document, Application, Job
from app.services.document_service import extract_text_from_file, create_chunks
from app.services.ai_service import generate_embedding, analyze_resume
from app.services.google_calendar import create_meeting_event
from app.services.gmail_service import send_google_email

# 1. Initialize Celery
celery_app = Celery(
    "worker",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)

# --- Helper: Get DB Session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# TASK 1: RAG DOCUMENT PROCESSING 
@celery_app.task(name="process_document_task")
def process_document_task(doc_id: int, file_path: str):
    """
    1. Reads PDF/DOCX.
    2. Splits into Chunks.
    3. Generates Embeddings (Vector).
    4. Saves to Supabase.
    """
    print(f"🚀 Processing Document ID: {doc_id}")
    db = SessionLocal()
    
    try:
        # Fetch the initial document record
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if not doc_record:
            return "Document not found in DB"

        # 1. Extract Text
        full_text = extract_text_from_file(file_path)
        if not full_text:
            print(f"❌ No text extracted from {file_path}")
            return "Empty file"

        # 2. Smart Chunking (Recursive)
        chunks = create_chunks(full_text)
        print(f"📄 Split into {len(chunks)} chunks.")

        # 3. Vectorization & Saving
        # Strategy: We update the original row with the 1st chunk, 
        # and create NEW rows for the remaining chunks.
        
        for i, chunk_text in enumerate(chunks):
            embedding_vector = generate_embedding(chunk_text)
            
            if i == 0:
                # Update the existing placeholder row
                doc_record.content = chunk_text
                doc_record.embedding = embedding_vector
            else:
                # Create new rows for extra chunks
                new_chunk = Document(
                    filename=f"{doc_record.filename} (Part {i+1})",
                    content=chunk_text,
                    embedding=embedding_vector,
                    company_id=doc_record.company_id
                )
                db.add(new_chunk)
        
        db.commit()
        print(f"✅ Document processed and indexed successfully!")
        
        # Cleanup: Delete local file after processing (Optional, saves space)
        if os.path.exists(file_path):
            os.remove(file_path)

        return "Success"

    except Exception as e:
        db.rollback()
        print(f"❌ Error in process_document_task: {e}")
        return f"Error: {str(e)}"
    finally:
        db.close()

# TASK 2: ATS RESUME SCANNER (The "Brain")
@celery_app.task(name="scan_resume_task")
def scan_resume_task(application_id: int, file_path: str):
    """
    1. Reads Candidate Resume.
    2. Fetches Job Description.
    3. Asks Groq AI to score it.
    4. Updates Application Status.
    """
    print(f"🕵️ Scanning Application ID: {application_id}")
    db = SessionLocal()

    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            return "Application not found"

        # Fetch Job Description
        job = db.query(Job).filter(Job.id == application.job_id).first()
        if not job:
            return "Job Description not found"

        # 1. Read Resume Text
        resume_text = extract_text_from_file(file_path)
        
        # 2. Save text to DB (so HR can read it later)
        application.resume_text = resume_text 
        db.commit()

        # 3. AI Analysis (Groq)
        ai_result = analyze_resume(resume_text, job.description)
        
        # 4. Save Score & Feedback
        application.match_score = ai_result.get("score", 0)
        application.ai_feedback = ai_result.get("summary", "No summary provided.")
        application.status = "Reviewed"
        
        db.commit()
        print(f"✅ Resume Scored: {application.match_score}/100")
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

        return "Success"

    except Exception as e:
        print(f"❌ Error in scan_resume_task: {e}")
        return f"Error: {str(e)}"
    finally:
        db.close()


# TASK 3 & 4: UTILS (Meeting & Email)
@celery_app.task(name="schedule_meeting_task")
def schedule_meeting_task(summary, start_time, end_time, emails):
    print(f"📅 Scheduling: {summary}")
    return create_meeting_event(summary, start_time, end_time, emails)

@celery_app.task(name="send_email_task")
def send_email_task(recipients, subject, body, file_paths=None):
    print(f"✉️ Sending email to {len(recipients)} recipients...")
    success = send_google_email(recipients, subject, body, file_paths)
    
    # Cleanup attachments if they were temp files
    if file_paths:
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)
                
    return "Sent" if success else "Failed"