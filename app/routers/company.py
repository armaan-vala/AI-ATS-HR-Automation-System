from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Company, User
from app.routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class CompanySettings(BaseModel):
    yearly_leaves: int

# 1. Update Company Settings (Only Admin)
@router.put("/settings")
def update_settings(
    settings: CompanySettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "hr_admin":
        raise HTTPException(status_code=403, detail="Only Admin can change settings")

    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company.yearly_leaves = settings.yearly_leaves
    db.commit()
    
    return {"message": f"Total Yearly Leaves updated to {settings.yearly_leaves}"}

# 2. Get Company Settings (For Admin Modal)
@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    return {"yearly_leaves": company.yearly_leaves}