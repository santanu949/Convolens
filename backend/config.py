import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "conversations.csv")
DB_PATH  = os.path.join(DATA_DIR, "convolens.db")

TOPIC_WINDOW_SIZE           = 3
TOPIC_SIMILARITY_THRESHOLD  = 0.35
KEYWORD_SHIFT_THRESHOLD     = 0.5
SHORT_CONVO_THRESHOLD       = 6
CHECKPOINT_INTERVAL         = 100
EMBEDDING_MODEL             = "all-MiniLM-L6-v2"
RETRIEVAL_EMBEDDING_THRESHOLD = 0.2
RETRIEVAL_TOP_K             = 5
HABIT_MIN_OCCURRENCES       = 3
UPLOAD_DIR                  = os.path.join(DATA_DIR, "uploads")
ALLOWED_EXTENSIONS          = {".csv"}
CORS_ORIGINS                = ["http://localhost:5173"]
FLASK_ENV                   = os.getenv("FLASK_ENV", "development")

# Additional needed constants
RETRIEVAL_TFIDF_THRESHOLD = 0.05
RETRIEVAL_FINAL_K = 3
EMBEDDING_WEIGHT = 0.6
TFIDF_WEIGHT = 0.4
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

KNOWN_JOB_TITLES = {
    "teacher", "engineer", "doctor", "nurse", "lawyer", "developer", "designer",
    "accountant", "manager", "analyst", "programmer", "scientist", "professor",
    "chef", "writer", "artist", "musician", "photographer", "therapist",
    "mechanic", "electrician", "plumber", "carpenter", "architect", "dentist",
    "pharmacist", "veterinarian", "pilot", "firefighter", "paramedic",
    "journalist", "editor", "librarian", "consultant", "entrepreneur",
    "barista", "waiter", "waitress", "cashier", "receptionist", "janitor",
    "intern", "student", "freelancer", "contractor", "tutor", "coach",
    "trainer", "counselor", "psychologist", "surgeon", "radiologist",
}
