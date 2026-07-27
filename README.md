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
- **Dockerized & Hugging Face Ready**: Prepared for Docker and 100% Free deployment on **Hugging Face Spaces** (16GB RAM).

---

## Quickstart Setup & Deployment

### Option 1: Deploy on Hugging Face Spaces (Free 16GB RAM + Public URL)

1. **Create a Free Space on Hugging Face**:
   - Go to [huggingface.co/new-space](https://huggingface.co/new-space)
   - Name: `gsstb-textbook-rag`
   - SDK: Select **Docker** (Blank)
   - Click **Create Space**

2. **Push Code to Hugging Face**:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_HF_USERNAME/gsstb-textbook-rag
   git push space main
   ```

---

### Option 2: Native Python Setup (Local Dev)

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

4. **Launch Application**:
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 7860
   ```

5. Open your browser at: **`http://localhost:7860`**

---

### Option 3: Local Docker Setup

```bash
docker build -t gsstb-rag .
docker run -p 7860:7860 gsstb-rag
```

Access the UI at **`http://localhost:7860`**.

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
