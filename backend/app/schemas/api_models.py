from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    book_name: str
    standard: Optional[str] = None
    subject: Optional[str] = None
    file_path: str
    total_pages: int
    total_chunks: int

class Citation(BaseModel):
    book_name: str
    page_number: int
    standard: Optional[str] = None
    subject: Optional[str] = None
    relevant_text: str
    score: float

class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or query")
    session_id: Optional[str] = Field(default="default_session", description="Conversation session ID")
    standard_filter: Optional[str] = Field(default=None, description="Optional filter by Std (e.g. 'Std 10')")
    subject_filter: Optional[str] = Field(default=None, description="Optional filter by Subject (e.g. 'Science')")

class ChatResponse(BaseModel):
    answer: str
    is_grounded: bool
    citations: List[Citation]
    session_id: str

class IngestionResponse(BaseModel):
    message: str
    book_name: str
    standard: Optional[str]
    subject: Optional[str]
    pages_processed: int
    chunks_created: int

class HealthResponse(BaseModel):
    status: str
    indexed_documents: int
    total_chunks: int
