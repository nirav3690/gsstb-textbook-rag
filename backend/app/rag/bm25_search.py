import re
from typing import List, Tuple, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.rag.chunker import Chunk

class BM25Index:
    def __init__(self):
        self.chunks: List[Chunk] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def _tokenize(self, text: str) -> List[str]:
        # Simple lower-cased word tokenization
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def add_chunks(self, new_chunks: List[Chunk]):
        self.chunks.extend(new_chunks)
        self.corpus_tokens = [self._tokenize(chunk.text) for chunk in self.chunks]
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = 10, filter_book: Optional[str] = None) -> List[Tuple[Chunk, float]]:
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        
        # Sort index by highest score
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0.0:
                continue
            chunk = self.chunks[idx]

            # Apply metadata filtering if specified
            if filter_book and chunk.book_name != filter_book:
                continue

            results.append((chunk, score))
            if len(results) >= top_k:
                break

        return results

    def clear(self):
        self.chunks = []
        self.corpus_tokens = []
        self.bm25 = None
