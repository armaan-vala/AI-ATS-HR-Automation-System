import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, get_password_hash
from app.celery_worker import send_email_task  # 🔥 Email Task Import kiya
from pydantic import BaseModel, EmailStr
from typing import List

router = APIRouter()

# --- Schemas ---
class EmployeeCreate(BaseModel):
    full_name: str
    email: EmailStr
    # Password HR will not generate, system will generate 

class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

# --- Helper: Generate Strong Random Password ---
def generate_random_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

# 1. ADD EMPLOYEE (Auto-Email Logic)
@router.post("/", response_model=EmployeeResponse)
def add_employee(
    emp_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "hr_admin":
        raise HTTPException(status_code=403, detail="Only HR Admins can add employees")

    # Check Duplicate
    existing_user = db.query(User).filter(User.email == emp_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 1. Generate Random Password
    raw_password = generate_random_password()
    hashed_password = get_password_hash(raw_password)

    # 2. Save to DB
    new_emp = User(
        full_name=emp_data.full_name,
        email=emp_data.email,
        hashed_password=hashed_password,
        role="employee",
        company_id=current_user.company_id
    )
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    # 3.  Trigger Celery to Send Welcome Email
    email_subject = "Welcome to TalentOS - Your Login Credentials"
    email_body = f"""
    <h3>Welcome aboard, {emp_data.full_name}!</h3>
    <p>You have been invited to join <b>TalentOS</b>.</p>
    <p>Here are your login details:</p>
    <ul>
        <li><b>URL:</b> <a href="http://127.0.0.1:8000/">Click here to Login</a></li>
        <li><b>Email:</b> {emp_data.email}</li>
        <li><b>Password:</b> {raw_password}</li>
    </ul>
    <p>Please login and change your password if needed.</p>
    <br>
    <p>Regards,<br>HR Team</p>
    """
    
    # Send email in background
    send_email_task.delay([emp_data.email], email_subject, email_body)
    
    return new_emp

# 2. LIST EMPLOYEES
@router.get("/", response_model=List[EmployeeResponse])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(User).filter(
        User.company_id == current_user.company_id,
        User.role == "employee"
    ).all()

# 3. DELETE EMPLOYEE
@router.delete("/{emp_id}")
def delete_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "hr_admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    emp = db.query(User).filter(User.id == emp_id, User.company_id == current_user.company_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.delete(emp)
    db.commit()
    return {"message": "Employee removed"}