from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, User, Conversation, Message
from app.routers.auth import get_current_user
from app.services.ai_service import generate_embedding, get_rag_answer
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: int

@router.post("/", response_model=ChatResponse)
async def chat_with_docs(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG Chat Endpoint:
    1. User Query -> Vector Embedding.
    2. Supabase Search -> Find matching docs (filtered by company_id).
    3. Groq -> Generate Answer based on found docs.
    """
    
    # 1. Manage Conversation History
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = Conversation(title=request.message[:30], user_id=current_user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save User Message
    user_msg = Message(content=request.message, sender="user", conversation_id=conversation.id)
    db.add(user_msg)
    
    # 2.  VECTOR SEARCH (The Core RAG Logic)
    query_vector = generate_embedding(request.message)
    
    if not query_vector:
        return {"response": "Error generating embeddings.", "conversation_id": conversation.id}

    
    similar_docs = db.query(Document).filter(
        Document.company_id == current_user.company_id
    ).order_by(
        Document.embedding.l2_distance(query_vector)
    ).limit(4).all()

    # 3. Prepare Context for AI
    context_chunks = [doc.content for doc in similar_docs if doc.content]
    
    if not context_chunks:
        # If no doc related then what llm will reply
        ai_response = "I couldn't find specific documents, but here is what I know: " + \
                      get_rag_answer(request.message, []) 
    else:
        # Real RAG Response
        ai_response = get_rag_answer(request.message, context_chunks)

    # 4. Save AI Response
    ai_msg = Message(content=ai_response, sender="ai", conversation_id=conversation.id)
    db.add(ai_msg)
    db.commit()

    return {
        "response": ai_response, 
        "conversation_id": conversation.id
    }