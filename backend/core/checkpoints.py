"""
Checkpoints — creates time-based checkpoints every CHECKPOINT_INTERVAL messages.
Summaries use cosine centrality: 3 most representative messages.
"""
from typing import List

from config import CHECKPOINT_INTERVAL
from models.message import Message
from models.segment import TimeCheckpoint
from storage.vector_store import vector_store
from storage import db

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine


def create_time_checkpoints(total_messages: int, progress_callback=None) -> List[TimeCheckpoint]:
    """
    Create checkpoints across ALL messages in chronological order.
    Reads messages from DB in chunks to avoid holding everything in RAM.
    """
    checkpoints = []
    interval = CHECKPOINT_INTERVAL

    for start in range(0, total_messages, interval):
        end = min(start + interval - 1, total_messages - 1)
        messages = db.get_messages_by_global_range(start, end)
        if not messages:
            continue

        summary = _centrality_summary(messages)
        cp = TimeCheckpoint(
            start_global_idx=messages[0].global_idx,
            end_global_idx=messages[-1].global_idx,
            summary=summary,
            message_count=len(messages),
        )
        checkpoints.append(cp)

        if progress_callback and len(checkpoints) % 50 == 0:
            pct = min(int((start / max(total_messages, 1)) * 100), 99)
            progress_callback("checkpoints", pct)

    return checkpoints


def _centrality_summary(messages: List[Message], top_n: int = 3) -> str:
    """Pick the top_n most central messages by average cosine similarity."""
    if len(messages) <= top_n:
        return " | ".join(f"{m.sender}: {m.text}" for m in messages)

    texts = [m.text for m in messages]
    embeddings = vector_store.encode(texts)

    if embeddings is None or len(embeddings) == 0:
        # Fallback: longest messages
        scored = sorted(messages, key=lambda m: len(m.text), reverse=True)
        return " | ".join(f"{m.sender}: {m.text}" for m in scored[:top_n])

    sim_matrix = sklearn_cosine(embeddings)
    avg_sims = sim_matrix.mean(axis=1)
    top_indices = sorted(avg_sims.argsort()[::-1][:top_n])

    return " | ".join(f"{messages[i].sender}: {messages[i].text}" for i in top_indices)
