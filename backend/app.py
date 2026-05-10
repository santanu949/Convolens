"""
Flask application factory — create_app pattern.
Serves React build in production, API routes via Blueprint.
"""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from config import CORS_ORIGINS, FLASK_ENV, DATA_DIR
from api.routes import api_bp
from api.middleware import register_error_handlers
from storage import db


def create_app():
    app = Flask(__name__, static_folder=None)

    # CORS
    CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

    # Ensure data directories exist
    os.makedirs(DATA_DIR, exist_ok=True)

    # Initialize database
    with app.app_context():
        db.init_db()
        if not db.is_processed():
            from config import CSV_PATH
            from services.processor import start_processing
            if os.path.exists(CSV_PATH):
                print("DB is empty. Auto-starting processing from CSV_PATH...")
                start_processing(CSV_PATH)

    # Register API routes
    app.register_blueprint(api_bp)

    # Register error handlers
    register_error_handlers(app)

    # In production, serve React build
    frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if os.path.isdir(frontend_dist):
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_react(path):
            if path.startswith('api/'):
                return {"error": "not found"}, 404
            # Try to serve static file first
            file_path = os.path.join(frontend_dist, path)
            if path and os.path.isfile(file_path):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

    return app


if __name__ == '__main__':
    from config import HOST, PORT
    application = create_app()
    print(f"Starting ConvoLens on http://{HOST}:{PORT}")
    application.run(host=HOST, port=PORT, debug=(FLASK_ENV == 'development'))
