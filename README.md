# GSSTB Textbook Conversational RAG System

A production-grade, conversational Retrieval-Augmented Generation (RAG) system built specifically to query Gujarat State School Textbook Board (GSSTB) Std 9–12 textbooks with **zero-hallucination strict grounding**, **hybrid search**, **precise page-number citations**, and a **modern web UI**.

---

## Key Features & Assignment Compliance

| Requirement | Implementation Detail | Status |
| :--- | :--- | :--- |
| **Multiple PDF Ingestion** | Page-level parser preserving 1-indexed page numbers & metadata | Completed |
| **Searchable RAG Pipeline** | Dense vector search (ChromaDB) + Sparse BM25 keyword search | Completed |
| **Single Chat Interface** | Modern dark-mode Glassmorphism web UI with real-time feedback | Completed |
| **Query Routing** | Auto-metadata tagging and optional Std 9–12 / Subject filters | Completed |
| **Strict Grounding** | Answers generated *only* from textbook snippets; strict refusal if absent | Completed |
| **Source Citations** | Returns **Source Textbook Name**, **Page Number(s)**, & **Exact Snippets** | Completed |
| **Conversational Context** | Multi-turn chat memory across questions | Completed |

### Bonus Features Included
- **Hybrid Search**: Dense Vector (ChromaDB) + BM25 Keyword Search combined via **Reciprocal Rank Fusion (RRF)**.
- **Reranking**: Integrated `FlashRank` lightweight cross-encoder reranking.
- **Metadata Filtering**: Filter queries by Standard (Std 9–12) or Subject (Science, Maths, etc.).
- **Page & Snippet Drawer**: Interactive source drawer showing full text snippet used for the answer.
- **Dockerized**: Containerized deployment with `Dockerfile` and `docker-compose.yml`.

---

## Project Structure

```
d:/RAG project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI Web App & Endpoints
│   │   ├── config.py            # Global settings & RAG parameters
│   │   ├── schemas/
│   │   │   └── api_models.py    # Pydantic request/response models
│   │   └── rag/
│   │       ├── parser.py        # Page-aware PDF parser
│   │       ├── chunker.py       # Metadata preserving chunker
│   │       ├── vectorstore.py   # ChromaDB vector store
│   │       ├── bm25_search.py   # BM25 sparse keyword index
│   │       ├── hybrid.py        # Hybrid retriever (Dense + BM25 + RRF)
│   │       ├── reranker.py      # FlashRank reranking
│   │       ├── memory.py        # Multi-turn conversation memory
│   │       └── generator.py     # Grounded LLM generator & citations
│   ├── requirements.txt
│   └── sample_data/
├── frontend/
│   ├── index.html               # Main Web Dashboard
│   ├── css/
│   │   └── style.css            # Dark mode Glassmorphism styles
│   └── js/
│       └── app.js               # Frontend chat & uploader logic
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quickstart Setup

### Option 1: Native Python Setup (Recommended for Local Dev)

1. **Clone & Navigate to Project Directory**:
   ```bash
   cd "d:/RAG project"
   ```

2. **Create & Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure Environment Variables** (Optional):
   Copy `.env.example` to `.env` if you want to supply an `OPENAI_API_KEY` or `GEMINI_API_KEY`. (Note: The system includes a built-in grounded extractive fallback if no API key is provided).
   ```bash
   cp .env.example .env
   ```

5. **Launch Application**:
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

6. Open your browser at: **`http://localhost:8000`**

---

### Option 2: Docker Compose Setup

Run the entire application in a Docker container with 1 command:

```bash
docker-compose up --build
```

Access the UI at **`http://localhost:8000`**.

---

## How to Use the Application

1. **Upload GSSTB Textbooks**:
   - Click the **`+` icon** in the left sidebar or the **Upload PDF** button.
   - Drag & drop any GSSTB textbook PDF (e.g., `Std_10_Science_GSSTB.pdf`).
   - The system automatically parses pages, extracts Standard/Subject metadata, creates vector embeddings, and builds the BM25 keyword index.

2. **Ask Questions**:
   - Type your question in the bottom input bar (e.g. *"What is Newton's second law of motion?"*).
   - Use the top filter dropdowns to restrict your query to a specific Standard (e.g., Std 10) or Subject (e.g., Science).

3. **Inspect Citations**:
   - Every answer displays clickable **Citation Badges** showing the **Book Name** and **Page Number**.
   - Click any citation badge to open the **Source Drawer** and inspect the exact text snippet retrieved from the PDF page.

4. **Test Out-of-Domain Refusal**:
   - Ask a question not covered in the uploaded textbooks (e.g., *"What is quantum computing?"*).
   - The system will refuse to hallucinate and strictly return:
     > *"I am sorry, but the requested information is unavailable in the provided textbook knowledge base."*

---

## API Documentation

- `POST /api/upload`: Upload textbook PDF file (`multipart/form-data`)
- `POST /api/chat`: Submit query + session ID + standard/subject filter
- `GET /api/documents`: Get list of ingested textbooks and statistics
- `DELETE /api/documents/{book_name}`: Delete textbook from index
- `DELETE /api/chat/{session_id}`: Clear session memory
- `GET /api/health`: System health & index count
