"""Message dataclass — lightweight container for parsed messages."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """A single message in a conversation."""
    id: Optional[int] = None
    conversation_id: int = 0
    sender: str = ""
    text: str = ""
    timestamp: Optional[str] = None
    global_idx: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "text": self.text,
            "timestamp": self.timestamp,
            "global_idx": self.global_idx,
        }
