"""
Processor — background task orchestration.
Runs CSV parsing, topic detection, checkpoints, and index building
in a background thread. Returns task_id immediately for polling.
"""
import os
import uuid
import threading
import traceback
from typing import Optional

from storage import db
from core.parser import parse_csv_streaming
from core.detector import detect_topics_for_conversation
from core.checkpoints import create_time_checkpoints
from services.retriever import retriever
from config import UPLOAD_DIR


def start_processing(csv_path: str = None) -> str:
    """
    Start background processing. Returns task_id for status polling.
    If DB is already processed, returns immediately.
    """
    task_id = str(uuid.uuid4())
    db.create_job(task_id)

    if db.is_processed():
        db.update_job(task_id, status="completed", progress=100, stage="ready")
        # Rebuild retriever index from existing DB data
        if not retriever.is_ready:
            threading.Thread(target=_rebuild_index, args=(task_id,), daemon=True).start()
        return task_id

    # Find CSV file
    if csv_path is None:
        csv_path = _find_csv()

    if csv_path is None or not os.path.exists(csv_path):
        db.update_job(task_id, status="error", error="No CSV file found. Please upload one first.")
        return task_id

    # Start background thread
    thread = threading.Thread(target=_process_pipeline, args=(task_id, csv_path), daemon=True)
    thread.start()

    return task_id


def _find_csv() -> Optional[str]:
    """Find the most recently uploaded CSV file, prioritizing CSV_PATH."""
    from config import CSV_PATH
    if os.path.exists(CSV_PATH):
        return CSV_PATH
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    csvs = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.csv')]
    if csvs:
        csvs.sort(key=lambda f: os.path.getmtime(os.path.join(UPLOAD_DIR, f)), reverse=True)
        return os.path.join(UPLOAD_DIR, csvs[0])
    return None


def _process_pipeline(task_id: str, csv_path: str):
    """Full processing pipeline running in a background thread."""
    try:
        def progress(stage, pct):
            db.update_job(task_id, stage=stage, progress=pct)

        # Stage 1: Parse CSV (0-30%)
        db.update_job(task_id, status="processing", stage="parsing", progress=0)
        total_msgs, total_convos = parse_csv_streaming(csv_path, progress_callback=progress)
        print(f"Parsed {total_msgs} messages from {total_convos} conversations")
        db.update_job(task_id, progress=30)

        # Stage 2: Topic Detection (30-70%)
        db.update_job(task_id, stage="detecting_topics", progress=30)
        _detect_all_topics(total_convos, lambda s, p: db.update_job(task_id, stage=s, progress=30 + int(p * 0.4)))
        print("Topic detection complete")

        # Stage 3: Time Checkpoints (70-80%)
        db.update_job(task_id, stage="checkpoints", progress=70)
        checkpoints = create_time_checkpoints(total_msgs, progress_callback=lambda s, p: None)
        db.insert_checkpoints_batch(checkpoints)
        print(f"Created {len(checkpoints)} time checkpoints")
        db.update_job(task_id, progress=80)

        # Stage 4: Build Retrieval Index (80-100%)
        db.update_job(task_id, stage="indexing", progress=80)
        retriever.build_index(progress_callback=lambda s, p: db.update_job(task_id, stage=s, progress=80 + int(p * 0.2)))

        # Mark complete
        db.mark_processed()
        db.update_job(task_id, status="completed", progress=100, stage="ready")
        print("Processing complete!")

    except Exception as e:
        traceback.print_exc()
        db.update_job(task_id, status="error", error=str(e))


def _detect_all_topics(total_convos: int, progress_callback):
    """Detect topics for each conversation, reading from DB one at a time."""
    for conv_id in range(total_convos):
        messages = db.get_messages_by_conversation(conv_id)
        if not messages:
            continue

        segments = detect_topics_for_conversation(messages, conv_id)
        if segments:
            db.insert_segments_batch(segments)

        if conv_id % 10 == 0:
            pct = min(int((conv_id / max(total_convos, 1)) * 100), 99)
            progress_callback("detecting_topics", pct)


def _rebuild_index(task_id: str):
    """Rebuild retriever index from existing DB data (fast, no reprocessing)."""
    try:
        retriever.build_index()
        db.update_job(task_id, status="completed", progress=100, stage="ready")
    except Exception as e:
        db.update_job(task_id, status="error", error=str(e))
