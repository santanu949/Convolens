"""
HTTP Routes — thin layer that calls services only. Zero business logic here.
"""
import os
import json
import time
from flask import Blueprint, request, jsonify

from api.middleware import validate_json, validate_pagination, validate_file_upload
from services.processor import start_processing
from services.retriever import retriever
from services.synthesizer import synthesize_answer
from services.persona import extract_persona_for_conversation
from storage import db
from config import UPLOAD_DIR

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "system_ready": db.is_processed() and retriever.is_ready,
        "total_messages": db.get_total_messages(),
        "total_conversations": db.get_total_conversations(),
    })


@api_bp.route('/upload', methods=['POST'])
@validate_file_upload
def upload_csv():
    """Accept CSV file upload (multipart), save to safe server directory."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file = request.files['file']
    # Sanitize filename
    safe_name = "conversations.csv"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    file.save(filepath)
    return jsonify({"status": "uploaded", "filename": safe_name})


@api_bp.route('/process', methods=['POST'])
def process():
    """Start background processing. Returns task_id immediately."""
    task_id = start_processing()
    return jsonify({"task_id": task_id, "status": "started"})


@api_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Get processing progress for a task."""
    job = db.get_job(task_id)
    if not job:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(job)


@api_bp.route('/query', methods=['POST'])
@validate_json('query')
def query():
    """Answer a question using RAG + persona data."""
    if not retriever.is_ready:
        return jsonify({"error": "System not ready. Please process data first."}), 400

    data = request.get_json()
    question = data['query'].strip()
    conversation_id = data.get('conversation_id')

    if not question:
        return jsonify({"error": "Empty query"}), 400

    start = time.time()

    # Retrieve relevant segments
    segments = retriever.search(question)

    # Get persona if conversation specified
    persona = None
    if conversation_id is not None:
        persona = db.get_persona(conversation_id)
        if persona is None:
            # Extract on demand
            messages = db.get_messages_by_conversation(conversation_id)
            if messages:
                persona_obj = extract_persona_for_conversation(messages, conversation_id)
                persona = persona_obj.to_dict()
                db.save_persona(conversation_id, json.dumps(persona))

    # Synthesize answer
    result = synthesize_answer(question, segments, persona)
    result["query_time_ms"] = round((time.time() - start) * 1000, 1)

    return jsonify(result)


@api_bp.route('/conversations', methods=['GET'])
@validate_pagination
def get_conversations():
    """Get paginated list of conversations."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    convos, total = db.get_conversations_paginated(page, per_page)
    return jsonify({
        "conversations": convos,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })


@api_bp.route('/conversations/<int:conv_id>/persona', methods=['GET'])
def get_persona_for_conversation(conv_id):
    """Get persona for a specific conversation (cached or extracted on demand)."""
    # Check cache
    persona = db.get_persona(conv_id)
    if persona is not None:
        return jsonify(persona)

    # Extract on demand
    messages = db.get_messages_by_conversation(conv_id)
    if not messages:
        return jsonify({"error": "Conversation not found"}), 404

    persona_obj = extract_persona_for_conversation(messages, conv_id)
    persona = persona_obj.to_dict()
    db.save_persona(conv_id, json.dumps(persona))
    return jsonify(persona)


@api_bp.route('/topics', methods=['GET'])
@validate_pagination
def get_topics():
    """Get paginated topic segments."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    conversation_id = request.args.get('conversation_id', None, type=int)
    segments, total = db.get_segments_paginated(page, per_page, conversation_id)
    return jsonify({
        "topics": segments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })


@api_bp.route('/checkpoints', methods=['GET'])
@validate_pagination
def get_checkpoints():
    """Get paginated time checkpoints."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    cps, total = db.get_checkpoints_paginated(page, per_page)
    return jsonify({
        "checkpoints": cps,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })
