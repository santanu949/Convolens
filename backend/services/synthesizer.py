"""
Answer Synthesizer — composes natural language answers from retrieved context.
Never dumps raw context. Always forms sentences grounded in evidence.
"""
import json
import re
from typing import Dict, Any, List, Optional

from storage import db


def synthesize_answer(query: str, retrieved_segments: List[Dict], persona: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate a natural language answer from retrieved context + persona.

    Returns dict with: answer, sources, confidence, query_type
    """
    query_lower = query.lower()
    query_type = _classify_query(query_lower)

    if query_type == "persona" and persona:
        answer = _persona_answer(query_lower, persona)
        confidence = "high" if persona.get("total_messages_analyzed", 0) > 5 else "medium"
    elif query_type == "habit" and persona:
        answer = _habit_answer(query_lower, persona)
        confidence = "high" if persona.get("habits") else "low"
    elif query_type == "communication" and persona:
        answer = _communication_answer(persona)
        confidence = "high"
    elif query_type == "interest" and persona:
        answer = _interest_answer(query_lower, persona, retrieved_segments)
        confidence = "medium"
    else:
        answer = _rag_answer(query_lower, retrieved_segments)
        confidence = _estimate_confidence(retrieved_segments)

    sources = [
        {
            "segment_id": s["segment_id"],
            "topic_label": s["topic_label"],
            "score": s["score"],
            "msg_range": s["msg_range"],
        }
        for s in retrieved_segments[:3]
    ]

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "query_type": query_type,
    }


def _classify_query(query: str) -> str:
    """Classify query intent."""
    persona_words = ['person', 'personality', 'trait', 'who is', 'what kind', 'describe', 'profile', 'character']
    habit_words = ['habit', 'routine', 'sleep', 'eat', 'exercise', 'daily', 'always do']
    comm_words = ['talk', 'speak', 'communicate', 'style', 'message', 'emoji', 'tone', 'write', 'type']
    interest_words = ['interest', 'hobby', 'like', 'enjoy', 'fun', 'favorite']

    if any(w in query for w in habit_words):
        return "habit"
    if any(w in query for w in comm_words):
        return "communication"
    if any(w in query for w in interest_words):
        return "interest"
    if any(w in query for w in persona_words):
        return "persona"
    return "general"


def _persona_answer(query: str, persona: Dict) -> str:
    """Compose answer about personality traits."""
    traits = persona.get("personality_traits", [])
    style = persona.get("communication_style", {})
    facts = persona.get("personal_facts", [])

    parts = []

    if traits:
        trait_names = [t["trait"] for t in traits[:4]]
        parts.append(f"Based on the conversation analysis, this user comes across as {', '.join(trait_names[:-1])}{' and ' + trait_names[-1] if len(trait_names) > 1 else trait_names[0]}.")

        for t in traits[:2]:
            if t.get("evidence"):
                ev = t["evidence"][0]["text"]
                parts.append(f"Their {t['trait']} side shows when they say things like: \"{ev}\"")

    if style:
        avg_w = style.get("avg_words_per_message", 0)
        desc = "short, concise" if avg_w < 10 else "moderate-length" if avg_w < 25 else "detailed, elaborate"
        parts.append(f"They tend to write {desc} messages (averaging {avg_w:.0f} words).")

    rel_facts = [f for f in facts if f["category"] == "relationship"]
    if rel_facts:
        rels = [f["value"] for f in rel_facts[:3]]
        parts.append(f"They've mentioned having a {', '.join(rels)} in their life.")

    return "\n".join(parts) if parts else "I couldn't find enough personality data for this conversation. Try selecting a longer conversation."


def _habit_answer(query: str, persona: Dict) -> str:
    """Compose answer about habits."""
    habits = persona.get("habits", [])

    if not habits:
        return "No strong habits were detected in this conversation. Habits require at least 3 mentions to be identified as a pattern."

    parts = [f"Based on their conversations, the following habits were detected (each mentioned 3+ times):\n"]

    for h in habits:
        parts.append(f"• **{h['category'].title()}** — {h['description']} (mentioned {h['occurrence_count']} times)")
        if h.get("evidence"):
            parts.append(f"  Example: \"{h['evidence'][0]['text']}\"")

    return "\n".join(parts)


def _communication_answer(persona: Dict) -> str:
    """Compose answer about communication style."""
    style = persona.get("communication_style", {})
    if not style:
        return "No communication data available for this conversation."

    avg_w = style.get("avg_words_per_message", 0)
    emoji_rate = style.get("emoji_usage_rate", 0)
    q_ratio = style.get("question_ratio", 0)
    excl_ratio = style.get("exclamation_ratio", 0)
    top_words = style.get("top_words", [])
    dist = style.get("message_length_distribution", {})

    length_desc = "brief and concise" if avg_w < 10 else "moderately detailed" if avg_w < 25 else "long and elaborate"
    emoji_desc = f"{emoji_rate:.1%} of messages" if emoji_rate > 0 else "rarely"

    parts = [
        f"They typically write {length_desc} messages, averaging {avg_w:.0f} words per message.",
        f"Emoji usage: {emoji_desc}.",
        f"About {q_ratio:.0%} of their messages contain questions, and {excl_ratio:.0%} use exclamation marks.",
    ]

    if top_words:
        parts.append(f"Their most frequently used words: {', '.join(top_words[:7])}.")

    if dist:
        parts.append(f"Message length breakdown: {dist.get('short', 0)} short, {dist.get('medium', 0)} medium, {dist.get('long', 0)} long messages.")

    return "\n".join(parts)


def _interest_answer(query: str, persona: Dict, segments: List[Dict]) -> str:
    """Compose answer about interests from persona + retrieved context."""
    facts = persona.get("personal_facts", [])
    prefs = [f for f in facts if f["category"] == "preference"]

    parts = []
    if prefs:
        parts.append("Based on their messages, they seem to enjoy:")
        for p in prefs[:5]:
            parts.append(f"• {p['value']}")
            if p.get("evidence"):
                parts.append(f"  (They said: \"{p['evidence'][0]['text']}\")")

    if segments:
        labels = list(set(s["topic_label"] for s in segments[:3]))
        parts.append(f"\nConversation topics that came up: {', '.join(labels)}.")

    return "\n".join(parts) if parts else "No specific interests were detected in this conversation."


def _rag_answer(query: str, segments: List[Dict]) -> str:
    """Compose answer from retrieved topic segments."""
    if not segments:
        return "I couldn't find relevant information in the conversations to answer that question. Try rephrasing or selecting a specific conversation."

    best = segments[0]
    parts = []

    parts.append(f"In conversations about **{best['topic_label']}**, here's what was discussed:")

    msgs = best.get("representative_messages", [])
    if msgs:
        for m in msgs[:3]:
            parts.append(f"• {m['sender']}: \"{m['text'][:120]}\"")

    if len(segments) > 1:
        second = segments[1]
        parts.append(f"\nRelated context from **{second['topic_label']}**: {second['summary'][:200]}")

    return "\n".join(parts)


def _estimate_confidence(segments: List[Dict]) -> str:
    if not segments:
        return "low"
    top_score = segments[0].get("score", 0)
    if top_score > 0.5:
        return "high"
    elif top_score > 0.25:
        return "medium"
    return "low"
