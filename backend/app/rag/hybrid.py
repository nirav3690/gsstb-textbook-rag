from typing import List, Tuple, Dict, Optional
from app.rag.chunker import Chunk
from app.rag.vectorstore import VectorStoreManager
from app.rag.bm25_search import BM25Index
from app.rag.reranker import Reranker
from app.config import settings

class HybridRetriever:
    def __init__(self, vectorstore: VectorStoreManager, bm25_index: BM25Index):
        self.vectorstore = vectorstore
        self.bm25_index = bm25_index
        self.reranker = Reranker()

    def reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[Chunk, float]],
        bm25_results: List[Tuple[Chunk, float]],
        k: int = 60
    ) -> List[Tuple[Chunk, float]]:
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}

        # Process dense vector search results
        for rank, (chunk, score) in enumerate(dense_results):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

        # Process BM25 keyword search results
        for rank, (chunk, score) in enumerate(bm25_results):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

        # Sort combined results by RRF score descending
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        combined: List[Tuple[Chunk, float]] = []
        for cid in sorted_cids:
            combined.append((chunk_map[cid], rrf_scores[cid]))

        return combined

    def retrieve(
        self,
        query: str,
        standard_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
        top_k: int = settings.FINAL_TOP_K
    ) -> List[Tuple[Chunk, float]]:
        # 1. Fetch dense candidates
        dense_candidates = self.vectorstore.search(
            query=query,
            top_k=settings.TOP_K_DENSE,
            standard_filter=standard_filter,
            subject_filter=subject_filter
        )

        # 2. Fetch BM25 keyword candidates
        bm25_candidates = self.bm25_index.search(
            query=query,
            top_k=settings.TOP_K_BM25
        )

        # 3. Fuse scores with Reciprocal Rank Fusion
        fused_candidates = self.reciprocal_rank_fusion(dense_candidates, bm25_candidates)

        # 4. Apply Reranking
        final_results = self.reranker.rerank(query=query, candidates=fused_candidates, top_k=top_k)

        return final_results
