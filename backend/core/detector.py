"""
Topic Detector — identifies topic shifts within conversations.

Algorithm:
- For conversations with >= SHORT_CONVO_THRESHOLD messages:
  Use sliding window (TOPIC_WINDOW_SIZE) embedding similarity.
  When cosine similarity between adjacent windows drops below
  TOPIC_SIMILARITY_THRESHOLD, mark a topic boundary.
- For short conversations (<SHORT_CONVO_THRESHOLD):
  Use keyword-shift detection (TF-IDF on first-half vs second-half).
  If cosine distance > KEYWORD_SHIFT_THRESHOLD, split.
- Summary: 3 most central sentences by average cosine similarity to all others.
- Label: top 3 TF-IDF keywords joined.
"""
import re
import numpy as np
from collections import Counter
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from config import (
    TOPIC_WINDOW_SIZE, TOPIC_SIMILARITY_THRESHOLD,
    KEYWORD_SHIFT_THRESHOLD, SHORT_CONVO_THRESHOLD,
)
from models.message import Message
from models.segment import TopicSegment
from storage.vector_store import vector_store


STOPWORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'you', 'your', 'yours',
    'he', 'him', 'his', 'she', 'her', 'hers', 'it', 'its', 'they', 'them',
    'their', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
    'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and',
    'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by',
    'for', 'with', 'about', 'against', 'between', 'through', 'during', 'before',
    'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on',
    'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
    'when', 'where', 'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'can', 'will', 'just', 'don', 'should', 'now',
    'hi', 'hello', 'hey', 'thanks', 'thank', 'yeah', 'yes', 'ok', 'okay',
    'sure', 'well', 'like', 'really', 'think', 'know', 'good', 'great',
    'nice', 'cool', 'awesome', 'sounds', 'right', 'got', 'go', 'going',
    'get', 'love', 'lot', 'much', 'also', 'would', 'could', 'thing', 'things',
    'time', 'way', 'one', 'say', 'said', 'user',
}


def detect_topics_for_conversation(messages: List[Message], conversation_id: int) -> List[TopicSegment]:
    """
    Detect topic segments within a single conversation.
    Returns list of TopicSegment objects.
    """
    if not messages:
        return []

    n = len(messages)

    if n < 2:
        return [_make_segment(messages, conversation_id, 0, n - 1)]

    if n < SHORT_CONVO_THRESHOLD:
        return _keyword_shift_detection(messages, conversation_id)
    else:
        return _sliding_window_detection(messages, conversation_id)


def _sliding_window_detection(messages: List[Message], conversation_id: int) -> List[TopicSegment]:
    """Use embedding similarity with sliding windows to detect topic changes."""
    n = len(messages)
    w = TOPIC_WINDOW_SIZE

    if n <= w * 2:
        return _keyword_shift_detection(messages, conversation_id)

    # Get embeddings for all messages
    texts = [m.text for m in messages]
    embeddings = vector_store.encode(texts)

    if embeddings is None or len(embeddings) == 0:
        # Fallback to keyword shift if embeddings unavailable
        return _keyword_shift_detection(messages, conversation_id)

    # Compute similarity between adjacent windows
    boundaries = [0]
    for i in range(w, n - w):
        window_before = embeddings[i - w:i]
        window_after = embeddings[i:i + w]

        # Average embedding for each window
        avg_before = np.mean(window_before, axis=0, keepdims=True)
        avg_after = np.mean(window_after, axis=0, keepdims=True)

        sim = float(sklearn_cosine(avg_before, avg_after)[0][0])
        if sim < TOPIC_SIMILARITY_THRESHOLD:
            # Only add if sufficiently far from last boundary
            if i - boundaries[-1] >= 2:
                boundaries.append(i)

    # Create segments from boundaries
    segments = []
    for bi in range(len(boundaries)):
        start = boundaries[bi]
        end = boundaries[bi + 1] - 1 if bi + 1 < len(boundaries) else n - 1
        seg_msgs = messages[start:end + 1]
        if seg_msgs:
            segments.append(_make_segment(seg_msgs, conversation_id, seg_msgs[0].global_idx, seg_msgs[-1].global_idx))

    return segments if segments else [_make_segment(messages, conversation_id, messages[0].global_idx, messages[-1].global_idx)]


def _keyword_shift_detection(messages: List[Message], conversation_id: int) -> List[TopicSegment]:
    """For short conversations: TF-IDF on first-half vs second-half."""
    n = len(messages)
    if n < 2:
        return [_make_segment(messages, conversation_id, messages[0].global_idx, messages[-1].global_idx)]

    mid = n // 2
    first_half = " ".join(m.text for m in messages[:mid])
    second_half = " ".join(m.text for m in messages[mid:])

    try:
        vectorizer = TfidfVectorizer(stop_words=list(STOPWORDS), max_features=200)
        tfidf = vectorizer.fit_transform([first_half, second_half])
        sim = float(sklearn_cosine(tfidf[0:1], tfidf[1:2])[0][0])
        distance = 1.0 - sim

        if distance > KEYWORD_SHIFT_THRESHOLD:
            seg1 = _make_segment(messages[:mid], conversation_id, messages[0].global_idx, messages[mid - 1].global_idx)
            seg2 = _make_segment(messages[mid:], conversation_id, messages[mid].global_idx, messages[-1].global_idx)
            return [seg1, seg2]
    except Exception:
        pass

    return [_make_segment(messages, conversation_id, messages[0].global_idx, messages[-1].global_idx)]


def _make_segment(messages: List[Message], conversation_id: int, start_idx: int, end_idx: int) -> TopicSegment:
    """Create a TopicSegment with label and summary."""
    label = _extract_label(messages)
    summary = _extract_summary(messages)
    return TopicSegment(
        conversation_id=conversation_id,
        start_idx=start_idx,
        end_idx=end_idx,
        topic_label=label,
        summary=summary,
        message_count=len(messages),
    )


def _extract_label(messages: List[Message]) -> str:
    """Extract top 3 TF-IDF keywords as topic label."""
    if not messages:
        return "general"
    texts = [m.text for m in messages]
    try:
        vectorizer = TfidfVectorizer(stop_words=list(STOPWORDS), max_features=100)
        tfidf = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        scores = np.asarray(tfidf.sum(axis=0)).flatten()
        top_indices = scores.argsort()[::-1][:3]
        keywords = [feature_names[i] for i in top_indices if scores[i] > 0]
        return ", ".join(keywords) if keywords else "general"
    except Exception:
        return "general"


def _extract_summary(messages: List[Message], max_sentences: int = 3) -> str:
    """Pick the 3 most central sentences by avg cosine similarity to all others."""
    if not messages:
        return ""
    if len(messages) <= max_sentences:
        return " | ".join(f"{m.sender}: {m.text}" for m in messages)

    texts = [m.text for m in messages]
    embeddings = vector_store.encode(texts)

    if embeddings is None or len(embeddings) == 0:
        # Fallback: pick longest messages
        scored = sorted(messages, key=lambda m: len(m.text), reverse=True)
        return " | ".join(f"{m.sender}: {m.text}" for m in scored[:max_sentences])

    # Compute pairwise similarities
    sim_matrix = sklearn_cosine(embeddings)
    avg_sims = sim_matrix.mean(axis=1)
    top_indices = avg_sims.argsort()[::-1][:max_sentences]
    top_indices = sorted(top_indices)

    return " | ".join(f"{messages[i].sender}: {messages[i].text}" for i in top_indices)
