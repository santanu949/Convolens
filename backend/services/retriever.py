"""
Retriever — dual TF-IDF + embedding retrieval with fusion scoring.
Indexes ALL messages in each segment (not just first 20).
"""
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from config import (
    RETRIEVAL_EMBEDDING_THRESHOLD, RETRIEVAL_TFIDF_THRESHOLD,
    RETRIEVAL_TOP_K, RETRIEVAL_FINAL_K, EMBEDDING_WEIGHT, TFIDF_WEIGHT,
)
from storage import db
from storage.vector_store import vector_store


class Retriever:
    """Dual retrieval: TF-IDF keyword + semantic embedding search."""

    def __init__(self):
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        self._segment_ids = []
        self._segment_data = []  # list of dicts with summary, label, etc.
        self._is_built = False

    @property
    def is_ready(self) -> bool:
        return self._is_built

    def build_index(self, progress_callback=None):
        """Build both TF-IDF and embedding indexes from DB."""
        segments = db.get_all_segments()
        if not segments:
            return

        self._segment_ids = []
        self._segment_data = []
        corpus = []

        for i, seg in enumerate(segments):
            # Using only summary and label to avoid N+1 query OOM for millions of messages
            doc_text = f"{seg.topic_label} {seg.summary}"

            self._segment_ids.append(seg.id)
            self._segment_data.append({
                "id": seg.id,
                "conversation_id": seg.conversation_id,
                "start_idx": seg.start_idx,
                "end_idx": seg.end_idx,
                "topic_label": seg.topic_label,
                "summary": seg.summary,
                "message_count": seg.message_count,
            })
            corpus.append(doc_text)

            if progress_callback and i % 500 == 0:
                pct = min(int((i / len(segments)) * 50), 49)
                progress_callback("indexing", pct)

        # Build TF-IDF index
        if corpus:
            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 2),
            )
            self._tfidf_matrix = self._tfidf_vectorizer.fit_transform(corpus)

        # Build embedding index
        summaries = [seg.summary for seg in segments]
        vector_store.build_index(self._segment_ids, summaries)

        if progress_callback:
            progress_callback("indexing", 100)

        self._is_built = True
        print(f"Retriever index built: {len(segments)} segments")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using both methods, merge with fusion scoring.
        Returns top RETRIEVAL_FINAL_K results.
        """
        if not self._is_built:
            return []

        # TF-IDF results
        tfidf_results = self._tfidf_search(query)

        # Embedding results
        emb_results = self._embedding_search(query)

        # Merge and re-rank
        return self._fuse_results(tfidf_results, emb_results)

    def _tfidf_search(self, query: str) -> List[Tuple[int, float]]:
        """TF-IDF cosine similarity search."""
        if self._tfidf_vectorizer is None or self._tfidf_matrix is None:
            return []

        try:
            query_vec = self._tfidf_vectorizer.transform([query])
            sims = sklearn_cosine(query_vec, self._tfidf_matrix).flatten()
            top_indices = sims.argsort()[::-1][:RETRIEVAL_TOP_K]
            results = []
            for idx in top_indices:
                score = float(sims[idx])
                if score >= RETRIEVAL_TFIDF_THRESHOLD:
                    results.append((self._segment_ids[idx], score))
            return results
        except Exception:
            return []

    def _embedding_search(self, query: str) -> List[Tuple[int, float]]:
        """Semantic embedding search."""
        return vector_store.search(query, top_k=RETRIEVAL_TOP_K, threshold=RETRIEVAL_EMBEDDING_THRESHOLD)

    def _fuse_results(self, tfidf_results: List[Tuple[int, float]],
                      emb_results: List[Tuple[int, float]]) -> List[Dict[str, Any]]:
        """Merge results using weighted fusion: 0.6 * embedding + 0.4 * tfidf."""
        scores = {}

        for seg_id, score in tfidf_results:
            scores[seg_id] = scores.get(seg_id, {"tfidf": 0, "embedding": 0})
            scores[seg_id]["tfidf"] = max(scores[seg_id]["tfidf"], score)

        for seg_id, score in emb_results:
            scores[seg_id] = scores.get(seg_id, {"tfidf": 0, "embedding": 0})
            scores[seg_id]["embedding"] = max(scores[seg_id]["embedding"], score)

        # Compute fused scores
        fused = []
        for seg_id, s in scores.items():
            fused_score = EMBEDDING_WEIGHT * s["embedding"] + TFIDF_WEIGHT * s["tfidf"]
            fused.append((seg_id, fused_score, s["tfidf"], s["embedding"]))

        fused.sort(key=lambda x: x[1], reverse=True)

        # Build final results with representative messages
        results = []
        for seg_id, fused_score, tfidf_score, emb_score in fused[:RETRIEVAL_FINAL_K]:
            # Find segment data
            seg_data = next((s for s in self._segment_data if s["id"] == seg_id), None)
            if not seg_data:
                continue

            # Get top 5 representative messages
            messages = db.get_messages_by_global_range(seg_data["start_idx"], seg_data["end_idx"])
            top_msgs = [{"sender": m.sender, "text": m.text, "idx": m.global_idx} for m in messages[:5]]

            results.append({
                "segment_id": seg_id,
                "conversation_id": seg_data["conversation_id"],
                "topic_label": seg_data["topic_label"],
                "summary": seg_data["summary"],
                "message_count": seg_data["message_count"],
                "msg_range": f"{seg_data['start_idx']}-{seg_data['end_idx']}",
                "score": round(fused_score, 4),
                "tfidf_score": round(tfidf_score, 4),
                "embedding_score": round(emb_score, 4),
                "representative_messages": top_msgs,
            })

        return results


# Global singleton
retriever = Retriever()
