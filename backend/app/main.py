import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas.api_models import (
    ChatRequest, ChatResponse, IngestionResponse, HealthResponse
)
from app.rag.parser import PDFBookParser
from app.rag.chunker import MetadataPreservingChunker
from app.rag.vectorstore import VectorStoreManager
from app.rag.bm25_search import BM25Index
from app.rag.hybrid import HybridRetriever
from app.rag.memory import ConversationMemory
from app.rag.generator import RAGGenerator

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Conversational RAG Application for GSSTB Textbooks"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Pipeline components
vectorstore = VectorStoreManager()
bm25_index = BM25Index()
chunker = MetadataPreservingChunker()
retriever = HybridRetriever(vectorstore, bm25_index)
memory = ConversationMemory()
generator = RAGGenerator()

# Sync BM25 index with existing ChromaDB vectorstore chunks on startup
try:
    existing_chunks = vectorstore.get_all_chunks()
    if existing_chunks:
        bm25_index.add_chunks(existing_chunks)
        print(f"[Startup] Loaded {len(existing_chunks)} existing chunks into BM25 index.")
except Exception as e:
    print(f"[Startup] Warning syncing BM25: {e}")


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    chunk_count = vectorstore.count()
    return HealthResponse(
        status="online",
        indexed_documents=len(set(c.book_name for c in vectorstore.get_all_chunks())),
        total_chunks=chunk_count
    )


@app.post("/api/upload", response_model=IngestionResponse)
def upload_textbook(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF textbook files are supported.")

    file_path = settings.UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Parse PDF page-by-page
        parser = PDFBookParser(str(file_path))
        pages = parser.parse()
        if not pages:
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF file.")

        # 2. Chunk text preserving metadata
        chunks = chunker.chunk_pages(pages)

        # 3. Add to ChromaDB vectorstore & BM25 index
        vectorstore.add_chunks(chunks)
        bm25_index.add_chunks(chunks)

        return IngestionResponse(
            message="Textbook successfully ingested and indexed.",
            book_name=parser.book_name,
            standard=parser.standard,
            subject=parser.subject,
            pages_processed=len(pages),
            chunks_created=len(chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting PDF: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = request.session_id or "default_session"

    # 1. Format history for memory
    history_str = memory.format_history_for_prompt(session_id)

    # 2. Retrieve relevant chunks using Hybrid Search & Reranking
    top_chunks = retriever.retrieve(
        query=request.message,
        standard_filter=request.standard_filter,
        subject_filter=request.subject_filter,
        top_k=settings.FINAL_TOP_K
    )

    # 3. Generate grounded response with citations
    response = generator.generate_response(
        query=request.message,
        context_chunks=top_chunks,
        conversation_history=history_str,
        session_id=session_id
    )

    # 4. Save to conversation memory
    memory.add_message(session_id, "user", request.message)
    memory.add_message(session_id, "assistant", response.answer)

    return response


@app.get("/api/documents")
def get_documents():
    chunks = vectorstore.get_all_chunks()
    books: Dict[str, Dict[str, Any]] = {}
    for c in chunks:
        if c.book_name not in books:
            books[c.book_name] = {
                "book_name": c.book_name,
                "standard": c.standard,
                "subject": c.subject,
                "pages": set(),
                "chunk_count": 0
            }
        books[c.book_name]["pages"].add(c.page_number)
        books[c.book_name]["chunk_count"] += 1

    result = []
    for bname, data in books.items():
        result.append({
            "book_name": data["book_name"],
            "standard": data["standard"],
            "subject": data["subject"],
            "total_pages": len(data["pages"]),
            "chunk_count": data["chunk_count"]
        })
    return result


@app.delete("/api/documents/{book_name}")
def delete_document(book_name: str):
    vectorstore.delete_book(book_name)
    # Refresh BM25
    remaining_chunks = vectorstore.get_all_chunks()
    bm25_index.clear()
    if remaining_chunks:
        bm25_index.add_chunks(remaining_chunks)
    return {"message": f"Document '{book_name}' deleted successfully."}


@app.delete("/api/chat/{session_id}")
def clear_session(session_id: str):
    memory.clear(session_id)
    return {"message": f"Session '{session_id}' memory cleared."}


# Serve Frontend static assets
frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/")
def read_root():
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "GSSTB Conversational RAG API Server is running."}
