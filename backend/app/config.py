import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "GSSTB Textbook Conversational RAG"
    VERSION: str = "1.0.0"
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Paths
    CHROMA_PERSIST_DIR: str = str(os.getenv("CHROMA_PERSIST_DIR", CHROMA_DIR))
    UPLOAD_DIR: Path = UPLOAD_DIR
    
    # Embeddings & Reranking
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")
    
    # RAG Parameters
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 600))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 120))
    TOP_K_DENSE: int = int(os.getenv("TOP_K_DENSE", 10))
    TOP_K_BM25: int = int(os.getenv("TOP_K_BM25", 10))
    FINAL_TOP_K: int = int(os.getenv("FINAL_TOP_K", 4))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.25))

settings = Settings()
