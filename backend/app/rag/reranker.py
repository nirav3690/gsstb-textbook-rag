from typing import List, Tuple
from app.rag.chunker import Chunk

class Reranker:
    def __init__(self):
        self.ranker = None
        try:
            from flashrank import Ranker
            # FlashRank is a tiny (~4MB), fast ONNX model for CPU reranking
            self.ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
        except Exception as e:
            print(f"[Reranker] FlashRank initialization skipped/unavailable: {e}. Falling back to default scoring.")

    def rerank(self, query: str, candidates: List[Tuple[Chunk, float]], top_k: int = 4) -> List[Tuple[Chunk, float]]:
        if not candidates:
            return []

        if not self.ranker:
            # Fallback: Sort candidates by existing similarity score
            sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
            return sorted_candidates[:top_k]

        try:
            from flashrank import RerankRequest
            passages = [
                {"id": idx, "text": chunk.text, "meta": chunk}
                for idx, (chunk, _) in enumerate(candidates)
            ]
            rerank_request = RerankRequest(query=query, passages=passages)
            results = self.ranker.rerank(rerank_request)

            reranked: List[Tuple[Chunk, float]] = []
            for item in results[:top_k]:
                chunk = item["meta"]
                score = float(item.get("score", 0.5))
                reranked.append((chunk, score))
            return reranked
        except Exception as e:
            print(f"[Reranker] Exception during reranking: {e}")
            sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
            return sorted_candidates[:top_k]
