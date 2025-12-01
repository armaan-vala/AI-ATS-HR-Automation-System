from pydantic import BaseModel, EmailStr
from typing import Optional, List

# --- AUTH SCHEMAS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str  

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- AGENT SCHEMAS ---
class AgentCreate(BaseModel):
    name: str
    role: str
    system_prompt: str

class AgentResponse(AgentCreate):
    id: int
    company_id: int
    class Config:
        from_attributes = True

# --- CHAT SCHEMAS ---
class ChatRequest(BaseModel):
    agent_id: int
    message: str
    conversation_id: Optional[int] = None