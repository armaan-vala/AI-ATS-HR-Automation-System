import os
from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.config import settings
import json

# 1. Initialize Embedding Model (Free & High Performance)

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Initialize Groq Client
client = Groq(api_key=settings.GROQ_API_KEY)

def generate_embedding(text: str):
    """Generates vector embedding for a given text string."""
    try:
        # Returns a list of floats (e.g., [0.1, -0.5, ...])
        return embedding_model.embed_query(text)
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None

def get_rag_answer(query: str, context_chunks: list[str]):
    """
    Sends the User Query + Retrieved Context to Groq Llama-3.
    """
    context_text = "\n\n".join(context_chunks)
    
    system_prompt = """You are a helpful HR Assistant for this company. 
    Answer the user's question strictly based on the Context provided below.
    If the answer is not in the context, say "I don't have information about that in the company documents."
    Do not hallucinate."""

    user_prompt = f"""
    Context:
    {context_text}

    Question: {query}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.1, # Low temperature for factual accuracy
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

def analyze_resume(resume_text: str, job_description: str):
    """
    ATS Logic: Compares Resume vs JD and returns JSON score.
    """
    prompt = f"""
    You are an expert ATS (Applicant Tracking System).
    
    Job Description:
    {job_description}
    
    Candidate Resume:
    {resume_text}
    
    Task:
    1. Evaluate the candidate's match score (0-100).
    2. List missing skills.
    3. Provide a brief summary.
    
    Output format must be strictly JSON:
    {{
        "score": 85,
        "missing_skills": ["Docker", "Kubernetes"],
        "summary": "Good candidate but lacks containerization experience."
    }}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"} # Ensures valid JSON
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"ATS Error: {e}")
        return {"score": 0, "error": str(e)}
    

def analyze_leave(reason: str, days: int):
    """
    Decides if leave should be Auto-Approved or Needs Review.
    """
    system_prompt = """
    You are an HR AI. Analyze the leave request.
    Rules:
    1. If reason is 'Sick'/'Fever'/'Personal' AND days <= 2: Recommend 'Auto-Approve'.
    2. If days > 3 OR reason implies vacation/trip: Recommend 'Human-Review'.
    
    Output JSON format: {"recommendation": "Auto-Approve" or "Human-Review", "reason": "Short explanation"}
    """
    
    user_prompt = f"Reason: {reason}, Duration: {days} days."

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"recommendation": "Human-Review", "reason": "AI Error"}