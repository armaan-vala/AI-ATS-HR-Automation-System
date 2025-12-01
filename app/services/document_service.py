import os
from PyPDF2 import PdfReader
import docx
from langchain.text_splitter import RecursiveCharacterTextSplitter

def extract_text_from_file(file_path: str) -> str:
    """
    Detects file type and extracts text accordingly.
    Supports: .pdf, .docx, .txt
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".pdf":
            return _extract_from_pdf(file_path)
        elif ext == ".docx":
            return _extract_from_docx(file_path)
        elif ext == ".txt":
            return _extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        print(f"❌ Error extracting text from {file_path}: {e}")
        return ""

def _extract_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def _extract_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def _extract_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def create_chunks(text: str, chunk_size=1000, overlap=200):
    """
    Splits text into smart chunks with overlap for better context.
    Overlap ensure karta hai ki baat beech me na kate.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_text(text)