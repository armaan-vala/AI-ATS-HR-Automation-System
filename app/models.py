from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector 
from app.database import Base

# --- 1. COMPANY (Multi-Tenancy Root) ---
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    yearly_leaves = Column(Integer, default=20)
    # Relationships
    users = relationship("User", back_populates="company")
    jobs = relationship("Job", back_populates="company")
    documents = relationship("Document", back_populates="company")
    agents = relationship("Agent", back_populates="company")

# --- 2. USERS (HR & Employees) ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="employee")  # 'hr_admin' or 'employee'
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    leaves = relationship("LeaveRequest", back_populates="user")

# --- 3. AI AGENTS (Chatbots) ---
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    role = Column(String)  
    system_prompt = Column(Text)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent")

# --- 4. RAG DOCUMENTS (Policy PDFs) ---
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)  # Extracted text
    
    #  Stores the vector embedding (1536 dimensions for standard models)
    embedding = Column(Vector(384)) 
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="documents")

# --- 5. ATS SYSTEM (Jobs & Resumes) ---
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    location = Column(String)
    status = Column(String, default="Open")
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String)
    candidate_email = Column(String)
    resume_text = Column(Text)  # Text extracted from PDF
    
    # AI Scoring
    match_score = Column(Float)  # e.g., 85.5
    ai_feedback = Column(Text)   # "Good skill match, lacks experience"
    status = Column(String, default="Applied") # Applied, Interview, Hired, Rejected
    
    job_id = Column(Integer, ForeignKey("jobs.id"))
    job = relationship("Job", back_populates="applications")

# --- 6. CHAT HISTORY ---
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

    user = relationship("User", back_populates="conversations")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    sender = Column(String) # 'user' or 'ai'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    conversation = relationship("Conversation", back_populates="messages")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(Text)
    start_date = Column(String) # Format: YYYY-MM-DD
    end_date = Column(String)
    days_count = Column(Integer)
    
    # Status: Pending, Approved, Rejected
    status = Column(String, default="Pending")
    
    # AI Analysis
    ai_recommendation = Column(String) # "Approve" or "Review"
    ai_reason = Column(Text) # "Minor illness, within limits"
    
    user = relationship("User", back_populates="leaves")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())