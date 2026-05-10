# ConvoLens — Conversation Intelligence RAG System

A fully local RAG-based chatbot that analyzes WhatsApp-style conversation data. Detects topic changes, builds user personas, and answers natural language queries using dual retrieval (TF-IDF + semantic embeddings).

**No paid APIs. No OpenAI. Fully local models.**

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐ │
│  │ ChatPanel│ │PersonaPnl│ │TopicPnl│ │CheckpointPnl │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └──────┬───────┘ │
│       └─────────────┴───────────┴─────────────┘         │
│                   services/api.js                        │
│              (ALL fetch calls here only)                 │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP
┌───────────────────────┴─────────────────────────────────┐
│                   Backend (Flask)                         │
│  ┌──────────────────────────────────────────────┐       │
│  │            api/routes.py (thin)               │       │
│  └──────────────────┬───────────────────────────┘       │
│     ┌───────────────┼───────────────────┐               │
│     ▼               ▼                   ▼               │
│  services/       services/          services/            │
│  processor.py    retriever.py       synthesizer.py       │
│  (background)    (dual index)       (NL answers)         │
│     │               │                                    │
│     ▼               ▼                                    │
│  core/parser.py  storage/vector_store.py                │
│  core/detector.py                                        │
│  core/checkpoints.py                                     │
│     │                                                    │
│     ▼                                                    │
│  storage/db.py ──── SQLite (persistent)                 │
└─────────────────────────────────────────────────────────┘
```

## How Topic Changes Are Detected

### Algorithm

The system processes messages **in strict chronological order within each conversation** using a dual strategy:

**For conversations with ≥6 messages (sliding window):**
1. Compute sentence embeddings for all messages using `all-MiniLM-L6-v2`
2. Slide a window of size **3** across the message sequence
3. At each position `i`, compute the **average embedding** of the window before `[i-3, i)` and after `[i, i+3)`
4. Compute cosine similarity between the two averaged embeddings
5. If similarity drops below **0.35**, mark position `i` as a topic boundary
6. Require minimum 2 messages between boundaries to avoid micro-segments

**For short conversations (<6 messages, keyword shift):**
1. Split messages into first-half and second-half
2. Build TF-IDF vectors (sklearn `TfidfVectorizer`) for each half
3. Compute cosine distance between the two vectors
4. If distance > **0.5**, mark a topic split at the midpoint

### Output Format
Each segment is stored with:
- `segment_id`, `conversation_id`, `start_idx`, `end_idx`
- `topic_label`: top 3 TF-IDF keywords from segment messages
- `summary`: 3 most central sentences (highest avg cosine similarity to all other sentences)

Example: `Topic 1 → msgs 0-7 → "sleep, tired, night" | Topic 2 → msgs 8-15 → "food, cooking, dinner"`

## How Retrieval Works

### Dual TF-IDF + Embedding Retrieval

**Two indexes built at processing time:**

1. **TF-IDF Index**: `sklearn.TfidfVectorizer` trained on ALL message text per segment (not just summaries). Max 10,000 features, unigrams + bigrams.
2. **Embedding Index**: Sentence embeddings of segment summaries using `all-MiniLM-L6-v2`.

**On query:**
1. Embed the query using the same model
2. Compute cosine similarity against all segment embeddings → top 5 (threshold: 0.2)
3. TF-IDF query against all segment text → top 5 (threshold: 0.05)
4. Merge by segment_id, deduplicate
5. Re-rank using fusion score: `0.6 × embedding_score + 0.4 × tfidf_score`
6. Return top 3 segments with summary, topic label, 5 representative messages, and confidence

## How Persona Is Built

### Critical Design Decision: Per-Conversation Scope

Persona is **NEVER** aggregated across conversations. Each extraction is scoped to a single `conversation_id` passed as parameter. This prevents the meaningless mixing of thousands of different users' data.

### Extraction Components

**Habits** (require 3+ occurrences):
- Categories: sleep, food, exercise, routine
- Pattern: regex-based detection with evidence message tracking
- Threshold: minimum 3 matches before marking as a habit

**Personal Facts**:
- Relationships: regex for "my wife/husband/mom/sister/etc."
- Occupation: matched against curated list of 50 known job titles (no false positives like "I'm not")
- Location: "I live in / I'm from / I moved to" patterns
- Preferences: "I love/enjoy/adore" patterns

**Personality Traits** (computed ratios):
- Curious: question_ratio > 0.2
- Expressive: exclamation_ratio > 0.15
- Humorous: lol/haha/😂 frequency > 0.03
- Empathetic: sorry/hope/care frequency > 0.05
- Positive/Negative: simple sentiment word-list scoring

**Communication Style** (statistical):
- Average words per message, emoji usage rate
- Question/exclamation ratios
- Top 10 words (excluding stopwords)
- Message length distribution (short/medium/long)
- Capitalization style analysis

**Every field includes an `evidence` array** with actual message snippets justifying the claim.

## Setup — Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend
```bash
cd convolens/backend
pip install -r requirements.txt
python app.py
# Server starts on http://localhost:5000
```

### Frontend
```bash
cd convolens/frontend
npm install
npm run dev
# Dev server on http://localhost:5173 (proxied to backend)
```

### Usage
1. Open http://localhost:5173
2. Click **Upload & Process CSV** and select your conversations.csv file
3. Wait for processing (progress bar shows status)
4. Select a conversation from the sidebar dropdown
5. Chat, explore persona, topics, and checkpoints

## Deployment

### Docker
```bash
docker-compose up --build
# App available at http://localhost:5000
```

### Render (one-click)
1. Push to GitHub
2. Connect repo on Render
3. `render.yaml` auto-configures the web service
4. Set any needed environment variables in Render dashboard

## Tech Stack
- **Backend**: Python, Flask, SQLite, sentence-transformers, scikit-learn
- **Frontend**: React 19, Vite, vanilla CSS
- **Embedding Model**: all-MiniLM-L6-v2 (local, free)
- **Deployment**: Docker, gunicorn

## Configuration
All tunable values in `backend/config.py`:
| Parameter | Default | Description |
|---|---|---|
| TOPIC_WINDOW_SIZE | 3 | Sliding window size for topic detection |
| TOPIC_SIMILARITY_THRESHOLD | 0.35 | Cosine similarity threshold for topic boundary |
| KEYWORD_SHIFT_THRESHOLD | 0.5 | TF-IDF distance threshold for short conversations |
| CHECKPOINT_INTERVAL | 100 | Messages per time checkpoint |
| RETRIEVAL_TOP_K | 5 | Candidates per retrieval method |
| RETRIEVAL_FINAL_K | 3 | Final results after fusion |
| EMBEDDING_WEIGHT | 0.6 | Weight for embedding scores in fusion |
| TFIDF_WEIGHT | 0.4 | Weight for TF-IDF scores in fusion |
| HABIT_MIN_OCCURRENCES | 3 | Minimum pattern matches for a habit |
