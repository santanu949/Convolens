"""
Vector store — embedding index for semantic retrieval.
Uses in-memory numpy arrays, loaded from DB on startup.
"""
import numpy as np
from typing import List, Tuple, Optional


class VectorStore:
    """In-memory embedding index for topic segments."""

    def __init__(self):
        self._embeddings = None  # shape: (n_segments, embed_dim)
        self._segment_ids = []   # parallel list of segment IDs
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                from config import EMBEDDING_MODEL
                print(f"Loading embedding model: {EMBEDDING_MODEL}...")
                self._model = SentenceTransformer(EMBEDDING_MODEL)
                print("Model loaded.")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self._model = None
        return self._model

    @property
    def is_ready(self) -> bool:
        return self._embeddings is not None and len(self._segment_ids) > 0

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts into embeddings."""
        if self.model is None:
            return np.array([])
        return self.model.encode(texts, show_progress_bar=False, batch_size=64)

    def build_index(self, segment_ids: List[int], texts: List[str]):
        """Build the embedding index from segment summaries."""
        if not texts or self.model is None:
            return
        self._segment_ids = segment_ids
        self._embeddings = self.encode(texts)
        print(f"Built embedding index: {len(segment_ids)} segments, dim={self._embeddings.shape[1]}")

    def search(self, query: str, top_k: int = 5, threshold: float = 0.2) -> List[Tuple[int, float]]:
        """Search for similar segments. Returns list of (segment_id, score)."""
        if not self.is_ready or self.model is None:
            return []

        query_emb = self.model.encode([query], show_progress_bar=False)
        sims = np.dot(self._embeddings, query_emb.T).flatten()
        top_indices = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score >= threshold:
                results.append((self._segment_ids[idx], score))
        return results


# Global singleton
vector_store = VectorStore()
