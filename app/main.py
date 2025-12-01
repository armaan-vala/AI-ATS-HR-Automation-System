import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import engine, Base

import app.models 
from app.routers import auth, ats, documents, chat, employees, leaves, company, tools

app = FastAPI(title=settings.PROJECT_NAME)

# --- 1. Mount Static Files ---
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- 2. Setup Templates ---
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# --- 3. Create Database Tables ---
Base.metadata.create_all(bind=engine)

# --- 4. Register API Routers ---
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(ats.router, prefix="/api/ats", tags=["ATS"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(leaves.router, prefix="/api/leaves", tags=["Leaves"])
app.include_router(company.router, prefix="/api/company", tags=["Company"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"]) 

# 5. FRONTEND ROUTES (HTML Pages)

# 🏠 Main Entry Point (Landing Page)
@app.get("/")
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

# Login route
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

# 📝 Signup Page
@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# 👔 Admin Dashboard
@app.get("/dashboard")
async def admin_dashboard(request: Request):
    # Ensure aapke templates folder me 'admin_dashboard.html' naam ki file ho
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

# 👋 Employee Dashboard
@app.get("/employee-dashboard")
async def employee_dashboard(request: Request):
    # Ensure aapke templates folder me 'employee_dashboard.html' naam ki file ho
    return templates.TemplateResponse("employee_dashboard.html", {"request": request})

# --- Feature Pages ---

@app.get("/jobs")
async def jobs_page(request: Request):
    return templates.TemplateResponse("jobs.html", {"request": request})

@app.get("/documents")
async def documents_page(request: Request):
    return templates.TemplateResponse("documents.html", {"request": request})

@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/manage-employees")
async def manage_employees_page(request: Request):
    return templates.TemplateResponse("manage_employees.html", {"request": request})

@app.get("/jobs/{job_id}/applicants")
async def applicants_page(request: Request, job_id: int):
    return templates.TemplateResponse("applicants.html", {"request": request})

@app.get("/create")
async def create_agent_page(request: Request):
    return templates.TemplateResponse("create_agent.html", {"request": request})

# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/admin/leave-requests")
async def admin_leaves_page(request: Request):
    return templates.TemplateResponse("admin_leaves.html", {"request": request})