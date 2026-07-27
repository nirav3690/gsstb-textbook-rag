import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.rag.chunker import Chunk

class VectorStoreManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        
        # Use SentenceTransformers embedding function
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
        
        self.collection = self.client.get_or_create_collection(
            name="gsstb_textbooks",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[Chunk]):
        if not chunks:
            return

        documents = [c.text for c in chunks]
        metadatas = [c.to_metadata() for c in chunks]
        ids = [c.chunk_id for c in chunks]

        # Batch upsert into ChromaDB
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        standard_filter: Optional[str] = None, 
        subject_filter: Optional[str] = None
    ) -> List[Tuple[Chunk, float]]:
        where_clause = {}
        if standard_filter and subject_filter:
            where_clause = {"$and": [{"standard": standard_filter}, {"subject": subject_filter}]}
        elif standard_filter:
            where_clause = {"standard": standard_filter}
        elif subject_filter:
            where_clause = {"subject": subject_filter}

        kwargs = {"query_texts": [query], "n_results": top_k}
        if where_clause:
            kwargs["where"] = where_clause

        res = self.collection.query(**kwargs)

        results: List[Tuple[Chunk, float]] = []
        if not res or not res.get("documents") or not res["documents"][0]:
            return results

        docs = res["documents"][0]
        metas = res["metadatas"][0]
        ids = res["ids"][0]
        distances = res["distances"][0] if "distances" in res and res["distances"] else [0.0] * len(docs)

        for doc, meta, cid, dist in zip(docs, metas, ids, distances):
            # ChromaDB cosine distance -> convert to cosine similarity score (1 - distance)
            sim_score = max(0.0, 1.0 - dist)
            chunk = Chunk(
                chunk_id=cid,
                text=doc,
                book_name=meta.get("book_name", "Unknown Book"),
                page_number=meta.get("page_number", 1),
                standard=meta.get("standard", "General"),
                subject=meta.get("subject", "General")
            )
            results.append((chunk, sim_score))

        return results

    def count(self) -> int:
        return self.collection.count()

    def get_all_chunks(self) -> List[Chunk]:
        res = self.collection.get(include=["documents", "metadatas"])
        chunks = []
        if res and res.get("documents"):
            for doc, meta, cid in zip(res["documents"], res["metadatas"], res["ids"]):
                chunks.append(Chunk(
                    chunk_id=cid,
                    text=doc,
                    book_name=meta.get("book_name", "Unknown Book"),
                    page_number=meta.get("page_number", 1),
                    standard=meta.get("standard", "General"),
                    subject=meta.get("subject", "General")
                ))
        return chunks

    def delete_book(self, book_name: str):
        self.collection.delete(where={"book_name": book_name})
