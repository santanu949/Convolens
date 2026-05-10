"""
Middleware — CORS, input validation, structured error responses.
"""
import os
from functools import wraps
from flask import request, jsonify

from config import ALLOWED_EXTENSIONS


def validate_json(*required_fields):
    """Decorator to validate required JSON fields in request body."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Invalid JSON body"}), 400
            for field in required_fields:
                if field not in data or data[field] is None:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def validate_pagination(f):
    """Decorator to validate pagination query params."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        if page < 1:
            return jsonify({"error": "page must be >= 1"}), 400
        if per_page < 1 or per_page > 100:
            return jsonify({"error": "per_page must be between 1 and 100"}), 400
        return f(*args, **kwargs)
    return wrapper


def validate_file_upload(f):
    """Decorator to validate CSV file uploads."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'file' not in request.files:
            return jsonify({"error": "No file provided. Use 'file' field in multipart form."}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"Invalid file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"}), 400
        return f(*args, **kwargs)
    return wrapper


def register_error_handlers(app):
    """Register structured JSON error handlers."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": str(e.description) if hasattr(e, 'description') else "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500
