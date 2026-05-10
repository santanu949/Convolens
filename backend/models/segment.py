"""TopicSegment and TimeCheckpoint dataclasses."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TopicSegment:
    """A segment of conversation about a single topic."""
    id: Optional[int] = None
    conversation_id: int = 0
    start_idx: int = 0
    end_idx: int = 0
    topic_label: str = ""
    summary: str = ""
    message_count: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "topic_label": self.topic_label,
            "summary": self.summary,
            "message_count": self.message_count,
        }


@dataclass
class TimeCheckpoint:
    """A time-based checkpoint every N messages."""
    id: Optional[int] = None
    start_global_idx: int = 0
    end_global_idx: int = 0
    summary: str = ""
    message_count: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "start_global_idx": self.start_global_idx,
            "end_global_idx": self.end_global_idx,
            "summary": self.summary,
            "message_count": self.message_count,
        }
