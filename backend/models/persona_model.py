"""Persona schema — structured output with evidence grounding."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PersonaEvidence:
    """A piece of evidence supporting a persona claim."""
    text: str = ""
    message_idx: int = 0

    def to_dict(self):
        return {"text": self.text, "message_idx": self.message_idx}


@dataclass
class Habit:
    category: str = ""
    description: str = ""
    occurrence_count: int = 0
    evidence: List[PersonaEvidence] = field(default_factory=list)

    def to_dict(self):
        return {
            "category": self.category,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class PersonalFact:
    category: str = ""
    value: str = ""
    evidence: List[PersonaEvidence] = field(default_factory=list)

    def to_dict(self):
        return {
            "category": self.category,
            "value": self.value,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class PersonalityTrait:
    trait: str = ""
    score: float = 0.0
    intensity: str = "mild"
    evidence: List[PersonaEvidence] = field(default_factory=list)

    def to_dict(self):
        return {
            "trait": self.trait,
            "score": round(self.score, 3),
            "intensity": self.intensity,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class CommunicationStyle:
    avg_words_per_message: float = 0.0
    avg_chars_per_message: float = 0.0
    emoji_usage_rate: float = 0.0
    question_ratio: float = 0.0
    exclamation_ratio: float = 0.0
    top_words: List[str] = field(default_factory=list)
    capitalization_style: str = "normal"
    punctuation_patterns: Dict[str, float] = field(default_factory=dict)
    message_length_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        return {
            "avg_words_per_message": round(self.avg_words_per_message, 1),
            "avg_chars_per_message": round(self.avg_chars_per_message, 1),
            "emoji_usage_rate": round(self.emoji_usage_rate, 4),
            "question_ratio": round(self.question_ratio, 3),
            "exclamation_ratio": round(self.exclamation_ratio, 3),
            "top_words": self.top_words,
            "capitalization_style": self.capitalization_style,
            "punctuation_patterns": {k: round(v, 3) for k, v in self.punctuation_patterns.items()},
            "message_length_distribution": self.message_length_distribution,
        }


@dataclass
class Persona:
    conversation_id: int = 0
    habits: List[Habit] = field(default_factory=list)
    personal_facts: List[PersonalFact] = field(default_factory=list)
    personality_traits: List[PersonalityTrait] = field(default_factory=list)
    communication_style: Optional[CommunicationStyle] = None
    total_messages_analyzed: int = 0

    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "habits": [h.to_dict() for h in self.habits],
            "personal_facts": [f.to_dict() for f in self.personal_facts],
            "personality_traits": [t.to_dict() for t in self.personality_traits],
            "communication_style": self.communication_style.to_dict() if self.communication_style else {},
            "total_messages_analyzed": self.total_messages_analyzed,
        }
