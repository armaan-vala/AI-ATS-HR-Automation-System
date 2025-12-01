from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models import User, LeaveRequest, Company
from app.routers.auth import get_current_user
from app.services.ai_service import analyze_leave
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# --- Schemas ---
class LeaveCreate(BaseModel):
    reason: str
    start_date: str
    end_date: str
    days: int

class LeaveAction(BaseModel):
    status: str # "Approved" or "Rejected"

# 1. EMPLOYEE SIDE (Apply)
@router.post("/apply")
def apply_leave(leave: LeaveCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. AI Analysis
    ai_result = analyze_leave(leave.reason, leave.days)
    
    # 2. Auto-Approval Logic
    final_status = "Pending"
    if ai_result.get("recommendation") == "Auto-Approve":
        final_status = "Approved" 

    new_leave = LeaveRequest(
        user_id=current_user.id,
        reason=leave.reason,
        start_date=leave.start_date,
        end_date=leave.end_date,
        days_count=leave.days,
        status=final_status,
        ai_recommendation=ai_result.get("recommendation", "Human-Review"),
        ai_reason=ai_result.get("reason", "Needs manual check")
    )
    db.add(new_leave)
    db.commit()
    return {"message": "Leave Applied", "status": final_status}

@router.get("/my-stats")
def get_leave_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    total_allocated = company.yearly_leaves if company and company.yearly_leaves else 20

    used_leaves = db.query(func.sum(LeaveRequest.days_count))\
        .filter(LeaveRequest.user_id == current_user.id, LeaveRequest.status == "Approved")\
        .scalar() or 0  

    approved_requests_count = db.query(LeaveRequest)\
        .filter(LeaveRequest.user_id == current_user.id, LeaveRequest.status == "Approved")\
        .count()
    
    return {
        "total_allocated": total_allocated,
        "balance": total_allocated - used_leaves,
        "accepted_count": approved_requests_count,
        "company_name": company.name if company else "Unknown"
    }

# 2. ADMIN SIDE (Review)

# Get All Requests for Company
@router.get("/company-requests")
def get_company_leaves(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "hr_admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    leaves = db.query(LeaveRequest).join(User)\
        .filter(User.company_id == current_user.company_id)\
        .order_by(desc(LeaveRequest.created_at))\
        .all()

    results = []
    for leave in leaves:
        # Dates YYYY-MM-DD string convert
        applied_on_str = leave.created_at.strftime("%Y-%m-%d") if leave.created_at else ""
        updated_on_str = leave.updated_at.strftime("%Y-%m-%d") if leave.updated_at else ""

        results.append({
            "id": leave.id,
            "employee_name": leave.user.full_name,
            "reason": leave.reason,
            "days": leave.days_count,
            "ai_recommendation": leave.ai_recommendation,
            "ai_reason": leave.ai_reason,
            "status": leave.status,
            "dates": f"{leave.start_date} to {leave.end_date}",
            "raw_start": leave.start_date,
            "raw_end": leave.end_date,
            "applied_on": applied_on_str,
            "updated_on": updated_on_str  
        })
    
    return results

# Approve/Reject Action
@router.put("/{leave_id}/action")
def update_leave_status(
    leave_id: int, 
    action: LeaveAction, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "hr_admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave.status = action.status
    db.commit()
    
    return {"message": f"Leave {action.status}"}