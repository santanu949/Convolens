"""
CSV Parser — streaming parser using Python's csv module.
Parses each conversation row, extracts messages, stores in SQLite immediately.
Does NOT hold 191K messages in memory.
"""
import csv
import re
import io
from typing import Generator, List, Tuple

from models.message import Message
from storage import db


# Pattern to match "User N: <text>"
_MSG_RE = re.compile(r'^(User\s*\d+)\s*:\s*(.+)$')


def parse_csv_streaming(filepath: str, progress_callback=None) -> Tuple[int, int]:
    """
    Parse the CSV file row by row, storing each conversation's messages
    into SQLite immediately. Never holds more than one conversation in memory.

    Returns:
        (total_messages, total_conversations)
    """
    global_idx = 0
    conversation_id = 0
    total_messages = 0

    # Count total rows for progress reporting
    total_rows = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            total_rows += 1
    # Rough estimate: each row is one conversation (header row subtracted if present)

    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)

        for row_idx, row in enumerate(reader):
            # Skip completely empty rows
            if not row or all(cell.strip() == '' for cell in row):
                continue

            # Each row is a conversation block (one or more cells, usually one quoted cell)
            conversation_text = ' '.join(row).strip()
            if not conversation_text:
                continue

            # Parse individual messages from the conversation text
            messages = _parse_conversation_block(conversation_text, conversation_id, global_idx)

            if messages:
                db.insert_messages_batch(messages)
                total_messages += len(messages)
                global_idx += len(messages)
                conversation_id += 1

            # Progress callback
            if progress_callback and row_idx % 500 == 0:
                pct = min(int((row_idx / max(total_rows, 1)) * 100), 99)
                progress_callback("parsing", pct)

    return total_messages, conversation_id


def _parse_conversation_block(text: str, conversation_id: int, start_global_idx: int) -> List[Message]:
    """Parse a single conversation block into Message objects."""
    messages = []
    local_idx = 0

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = _MSG_RE.match(line)
        if match:
            sender = match.group(1).strip()
            msg_text = match.group(2).strip()
            if msg_text:
                messages.append(Message(
                    conversation_id=conversation_id,
                    sender=sender,
                    text=msg_text,
                    global_idx=start_global_idx + local_idx,
                ))
                local_idx += 1

    return messages


def get_conversation_count_from_csv(filepath: str) -> int:
    """Quick count of non-empty rows in CSV."""
    count = 0
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and any(cell.strip() for cell in row):
                count += 1
    return count
