import os
import sys
from pathlib import Path
import streamlit as st

# Add backend directory to sys.path (insert at position 0 to prioritize over CWD)
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.rag.parser import PDFBookParser
from app.rag.chunker import MetadataPreservingChunker
from app.rag.vectorstore import VectorStoreManager
from app.rag.bm25_search import BM25Index
from app.rag.hybrid import HybridRetriever
from app.rag.memory import ConversationMemory
from app.rag.generator import RAGGenerator
from app.config import settings

# Page Configuration
st.set_page_config(
    page_title="GSSTB Textbook AI Tutor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark Mode & Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+Gujarati:wght@400;600;700&display=swap');
    .main { background-color: #0B0F19; font-family: 'Noto Sans Gujarati', 'Inter', sans-serif; }
    .stApp { background-color: #0B0F19; color: #F9FAFB; font-family: 'Noto Sans Gujarati', 'Inter', sans-serif; }
    .citation-box {
        background-color: #1F2937;
        border-left: 4px solid #6366F1;
        padding: 10px 14px;
        margin-top: 8px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #6366F1, #4F46E5);
        color: white;
        border: none;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Singleton RAG Pipeline
@st.cache_resource
def get_rag_pipeline():
    vectorstore = VectorStoreManager()
    bm25_index = BM25Index()
    chunker = MetadataPreservingChunker()
    retriever = HybridRetriever(vectorstore, bm25_index)
    memory = ConversationMemory()
    generator = RAGGenerator()
    
    # Sync existing chunks on startup
    try:
        existing_chunks = vectorstore.get_all_chunks()
        if existing_chunks:
            bm25_index.add_chunks(existing_chunks)
    except Exception as e:
        print(f"BM25 Sync warning: {e}")
        
    return vectorstore, bm25_index, chunker, retriever, memory, generator

vectorstore, bm25_index, chunker, retriever, memory, generator = get_rag_pipeline()

# Session Chat History State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Navigation & PDF Uploader
with st.sidebar:
    st.title("📚 GSSTB RAG System")
    st.caption("Gujarat Board Std 9–12 AI Tutor")
    
    st.divider()
    st.subheader("📤 Upload Textbook PDF")
    uploaded_file = st.file_uploader("Choose a GSSTB PDF Textbook", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("⚡ Process & Index Textbook", use_container_width=True, type="primary"):
            progress_bar = st.progress(0, text="Starting PDF processing...")
            status_text = st.empty()
            save_path = settings.UPLOAD_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                parser = PDFBookParser(str(save_path))
                
                def update_pdf_progress(current_page, total_pages, method="Extracting"):
                    pct = int(5 + (current_page / max(1, total_pages)) * 45)
                    progress_bar.progress(pct, text=f"{method}: page {current_page} of {total_pages}...")

                pages = parser.parse(progress_callback=update_pdf_progress)
                
                if not pages:
                    st.error("⚠️ Could not extract text from this PDF. It may be a scanned image PDF without a text layer.")
                    if not settings.GEMINI_API_KEY:
                        st.warning("💡 **Tip**: Set a `GEMINI_API_KEY` in Streamlit Cloud Secrets to enable automatic OCR for legacy Gujarati font PDFs.")
                    progress_bar.empty()
                else:
                    progress_bar.progress(50, text=f"Chunking {len(pages)} pages...")
                    chunks = chunker.chunk_pages(pages)
                    
                    if not chunks:
                        st.error("⚠️ No text chunks could be created from the extracted pages.")
                        progress_bar.empty()
                    else:
                        progress_bar.progress(75, text="Creating embeddings & indexing into ChromaDB + BM25...")
                        vectorstore.add_chunks(chunks)
                        bm25_index.add_chunks(chunks)
                        
                        progress_bar.progress(100, text="Indexing complete!")
                        method_info = f" | Method: {parser.extraction_method}" if hasattr(parser, 'extraction_method') else ""
                        st.success(f"✅ Ingested '{parser.book_name}' ({len(pages)} pages, {len(chunks)} chunks{method_info})")
                        if parser.is_legacy_font and parser.extraction_method.startswith("PyMuPDF"):
                            st.warning("⚠️ This PDF uses a legacy Gujarati font. Text contains encoding artifacts.")
                            if getattr(parser, 'ocr_error', ''):
                                st.error(f"❌ OCR Error details: {parser.ocr_error}")
                            elif not settings.GEMINI_API_KEY:
                                st.info("💡 Enter your Gemini API Key in the sidebar above to run automatic Vision OCR.")
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Error processing PDF: {e}")
                progress_bar.empty()

    st.divider()
    st.subheader("📚 Knowledge Base")
    chunks = vectorstore.get_all_chunks()
    books = {}
    for c in chunks:
        if c.book_name not in books:
            books[c.book_name] = {"std": c.standard, "sub": c.subject, "pages": set()}
        books[c.book_name]["pages"].add(c.page_number)
    
    if books:
        for bname, meta in books.items():
            col_b1, col_b2 = st.columns([4, 1])
            with col_b1:
                st.markdown(f"**📖 {bname}**")
                st.caption(f"🏷️ {meta['std']} | {meta['sub']} | 📄 {len(meta['pages'])} Pages")
            with col_b2:
                if st.button("🗑️", key=f"del_{bname}", help=f"Delete {bname}"):
                    vectorstore.delete_book(bname)
                    remaining = vectorstore.get_all_chunks()
                    bm25_index.clear()
                    if remaining:
                        bm25_index.add_chunks(remaining)
                    st.success(f"Deleted '{bname}'")
                    st.rerun()
    else:
        st.info("No textbooks indexed yet. Upload a PDF above.")

    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main Chat Interface
st.title("💬 Textbook Conversational Assistant")
st.markdown("Ask questions strictly based on uploaded Gujarat State Board textbooks.")

# Filter Controls
col1, col2 = st.columns(2)
with col1:
    filter_std = st.selectbox("Standard Filter:", ["All Standards", "Std 9", "Std 10", "Std 11", "Std 12"])
with col2:
    filter_sub = st.selectbox("Subject Filter:", ["All Subjects", "Science", "Mathematics", "Social Science", "Physics", "Chemistry", "Biology", "GruhVigyan"])

std_val = None if filter_std == "All Standards" else filter_std
sub_val = None if filter_sub == "All Subjects" else filter_sub

# Render Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "citations" in message and message["citations"]:
            with st.expander("📌 View Source Citations & Relevant Snippets"):
                for cit in message["citations"]:
                    st.markdown(f"""
                    <div class="citation-box">
                        <strong>📖 {cit.book_name} (Page {cit.page_number})</strong><br>
                        <em>{cit.standard or ''} {cit.subject or ''}</em><br><br>
                        "{cit.relevant_text}"
                    </div>
                    """, unsafe_allow_html=True)

# User Query Input
if prompt := st.chat_input("Ask a question from GSSTB textbooks..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching textbook knowledge base & generating answer..."):
            top_chunks = retriever.retrieve(
                query=prompt,
                standard_filter=std_val,
                subject_filter=sub_val,
                top_k=settings.FINAL_TOP_K
            )
            
            try:
                response = generator.generate_response(
                    query=prompt,
                    context_chunks=top_chunks,
                    session_id="streamlit_session",
                    target_language="English"
                )
            except TypeError:
                st.cache_resource.clear()
                from app.rag.generator import RAGGenerator
                generator = RAGGenerator()
                response = generator.generate_response(
                    query=prompt,
                    context_chunks=top_chunks,
                    session_id="streamlit_session",
                    target_language="English"
                )
            
            st.markdown(response.answer)
            
            if response.citations:
                with st.expander("📌 View Source Citations & Relevant Snippets"):
                    for cit in response.citations:
                        st.markdown(f"""
                        <div class="citation-box">
                            <strong>📖 {cit.book_name} (Page {cit.page_number})</strong><br>
                            <em>{cit.standard or ''} {cit.subject or ''}</em><br><br>
                            "{cit.relevant_text}"
                        </div>
                        """, unsafe_allow_html=True)
                        
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.answer,
                "citations": response.citations
            })
