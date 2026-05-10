<div align="center">

# ConvoLens

**A production-ready RAG-based conversational intelligence platform**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)

ConvoLens analyzes large-scale WhatsApp-style conversation datasets using
Retrieval-Augmented Generation (RAG), semantic topic detection, and
structured persona extraction — with zero external API dependencies.

[Live Demo](https://convolens.onrender.com) · [Report Bug](https://github.com/santanu949/Convolens/issues) · [Request Feature](https://github.com/santanu949/Convolens/issues)

</div>

---

## Overview

Most RAG systems treat documents as static text blobs. Real conversations
are different — they evolve over time, shift between topics, and reveal
personality through patterns of language.

ConvoLens was built to solve a specific problem: given a massive CSV of
WhatsApp-style conversations (191,592 messages across 11,001 conversations),
how do you build a system that can answer natural language questions about
the data intelligently — without hallucinating, without dumping raw text,
and without relying on any paid APIs?

The answer is a three-part pipeline:

1. **Chronological topic segmentation** — detect when conversations shift
   topic and build summaries of each segment independently.
2. **Grounded persona extraction** — extract habits, traits, facts, and
   communication style from individual conversations with real message
   evidence backing every claim.
3. **Dual-index RAG retrieval** — fuse semantic embedding search with
   TF-IDF keyword search to find the most relevant context, then synthesize
   a natural language answer — never a raw context dump.

---

## Key Features

### Intelligent Processing
- **Stream-based CSV parsing** — processes 191K+ messages row by row with
  zero memory overflow. No pandas. Pure Python csv module writing to SQLite
  in real time.
- **Chronological ordering guaranteed** — every message is processed in
  strict temporal sequence before any analysis begins.
- **SQLite persistence** — the 5-10 minute initial processing run happens
  exactly once. Every subsequent server start loads from the database
  instantly.

### Topic Detection System
- **Sliding window detection** — groups of 3 consecutive messages are
  embedded and compared. When cosine similarity drops below 0.35, a topic
  boundary is recorded.
- **Short conversation fallback** — conversations under 6 messages use a
  TF-IDF keyword-shift heuristic instead (cosine distance threshold: 0.5).
- **Segment summaries** — each topic segment gets a label (top 3 TF-IDF
  keywords) and an extractive summary (3 most central sentences by cosine
  centrality).
- **Output format:**
  ```
  Topic 1 → messages 1–18  → [summary of segment]
  Topic 2 → messages 19–34 → [summary of segment]
  Topic 3 → messages 35–52 → [summary of segment]
  ```

### 100-Message Time Checkpoints
- Independently of topic detection, a summary checkpoint is created for
  every 100 messages in chronological order across the entire dataset.
- These are separately indexed and retrievable alongside topic segments.

### Dual-Index RAG Retrieval
- **Embedding index** — all-MiniLM-L6-v2 (384-dimensional) encodes all
  segment summaries for semantic similarity search.
- **TF-IDF index** — sklearn TfidfVectorizer indexes full segment text for
  exact keyword matching.
- **Fusion scoring** — `final_score = (0.6 × embedding_score) + (0.4 × tfidf_score)`
- **Threshold filtering** — only segments scoring above 0.20 are returned.
- **Top 3 segments** are passed to the synthesizer with source citations.

### Per-Conversation Persona Extraction
Persona is scoped strictly to a single conversation — never aggregated
across multiple conversations.

From User 1's messages in the selected conversation:

| Category | What is extracted | Validation rule |
|---|---|---|
| Habits | Sleep patterns, food, exercise, routines | Requires 3+ occurrences |
| Personal facts | Relationships, location, occupation | Occupation matched against curated 50-title list only |
| Personality traits | Curious, expressive, humorous, empathetic | Computed from message ratios |
| Communication style | Avg word count, emoji rate, tone, top words | Statistical analysis of full message history |

Every field includes an `evidence` array with direct message quotes.

### Answer Synthesis
The synthesizer classifies every query into one of four types — persona,
habit, communication, or general — and composes a natural language answer
grounded in the retrieved context. Raw JSON dumps and raw context pastes are
never shown to the user.

---

## System Architecture

```
conversations.csv (191,592 messages)
         │
         ▼
┌─────────────────────┐
│   core/parser.py    │  Stream-reads CSV row by row
│   (csv module)      │  Writes to SQLite immediately
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  core/detector.py   │  Window=3 sliding embeddings
│  core/checkpoints   │  Topic splits + 100-msg chunks
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  storage/db.py      │  SQLite — messages, segments,
│  storage/vector_    │  checkpoints, personas, jobs
│  store.py           │  Numpy embedding arrays
└────────┬────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────────┐
│services│ │services/         │
│/retrie-│ │persona.py        │
│ver.py  │ │                  │
│TF-IDF +│ │Per-conversation  │
│Embeddi-│ │habit/trait/fact  │
│ng Fuse │ │extraction with   │
└───┬────┘ │evidence arrays   │
    │      └──────────────────┘
    ▼
┌─────────────────────┐
│services/synthesizer │  Natural language answer
│.py                  │  generation with citations
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   api/routes.py     │  Flask REST API
│   Flask factory     │  Zero business logic in routes
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  React Frontend     │  ChatPanel, PersonaPanel,
│  (Vite + JS)        │  TopicPanel, CheckpointPanel
└─────────────────────┘
```

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Core runtime |
| Flask | 3.1.1 | REST API server (factory pattern) |
| Flask-CORS | 5.0.1 | Cross-origin request handling |
| sentence-transformers | 3.0+ | Semantic embeddings (all-MiniLM-L6-v2) |
| scikit-learn | 1.4+ | TF-IDF vectorization |
| numpy | 1.26+ | Vector math and cosine similarity |
| scipy | 1.10+ | Distance computation |
| SQLite3 | built-in | Persistent storage |
| Gunicorn | 22.0+ | Production WSGI server |
| python-dotenv | 1.0+ | Environment configuration |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| Vite | 6 | Build tool and dev server |
| JavaScript (ES2022) | — | Language (no TypeScript) |
| CSS Custom Properties | — | Theming and dark mode |
| Context + useReducer | — | State management (no Redux) |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker | Containerized builds |
| Render | Cloud deployment (free tier) |
| GitHub Actions | CI/CD pipeline |

---

## Setup and Installation

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- Git

### 1. Clone the repository

```bash
git clone https://github.com/santanu949/Convolens.git
cd Convolens
```

### 2. Add your dataset

Place your `conversations.csv` file at:
```
backend/data/conversations.csv
```

The CSV should have one conversation per row, with messages separated by
line breaks within each quoted cell.

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Start the backend

```bash
cd backend
python app.py
```

On first run with an empty database, processing starts automatically:
```
DB is empty. Auto-starting processing from CSV_PATH...
Parsed 191592 messages from 11001 conversations
Running on http://127.0.0.1:5000
```

Processing takes 5–15 minutes on first run. All subsequent starts load
from the database instantly.

### 6. Start the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Usage Guide

### Chat Panel
Type any natural language question about the conversations:
- `"What kind of person is this user?"`
- `"What are their habits?"`
- `"How do they talk?"`
- `"What topics do they discuss most?"`

The system retrieves relevant topic segments and generates a grounded answer
with source citations showing which segment the answer came from.

### Topics Panel
Browse all detected topic segments in chronological order:
```
Topic 1 → messages 1–18  → User discusses moving to Portland and Powell's Books
Topic 2 → messages 19–34 → Conversation shifts to music and punk bands
Topic 3 → messages 35–52 → Plans to meet up for pizza
```

### Persona Panel
Select any conversation from the dropdown. The system extracts and displays:
- Habits detected with supporting evidence messages
- Personal facts (relationships, location, occupation)
- Personality traits with computed ratios
- Communication style statistics

### Checkpoints Panel
Browse time-based summaries created every 100 messages, independent of
topic boundaries.

---

## Project Structure

```
Convolens/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # HTTP routes only — zero business logic
│   │   └── middleware.py      # CORS, validation, error handling
│   ├── services/
│   │   ├── __init__.py
│   │   ├── processor.py       # Background task orchestration
│   │   ├── retriever.py       # Dual TF-IDF + embedding retrieval
│   │   ├── synthesizer.py     # Natural language answer generation
│   │   └── persona.py         # Per-conversation persona extraction
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parser.py          # Stream CSV parser (no pandas)
│   │   ├── detector.py        # Topic change detection
│   │   └── checkpoints.py     # 100-message checkpoint creation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── message.py         # Message dataclass
│   │   ├── segment.py         # TopicSegment + TimeCheckpoint
│   │   └── persona_model.py   # Persona schema with evidence arrays
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py              # SQLite connection + schema
│   │   └── vector_store.py    # Numpy embedding index
│   ├── data/
│   │   └── .gitkeep           # Place conversations.csv here
│   ├── __init__.py
│   ├── config.py              # All configuration values
│   ├── app.py                 # Flask factory (create_app)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx
│   │   │   ├── PersonaPanel.jsx
│   │   │   ├── TopicPanel.jsx
│   │   │   ├── CheckpointPanel.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── MessageBubble.jsx
│   │   ├── hooks/
│   │   │   ├── useChat.js
│   │   │   └── useProcessing.js
│   │   ├── services/
│   │   │   └── api.js         # All fetch() calls — never in components
│   │   ├── store/
│   │   │   └── index.js       # useReducer + Context
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── .gitignore
└── README.md
```

---

## Current Status

| Component | Status | Notes |
|---|---|---|
| System Architecture | Complete | Strict layered separation |
| CSV Stream Parser | Complete | 191K messages, zero OOM |
| Topic Detection | Complete | Window=3, cosine threshold=0.35 |
| 100-msg Checkpoints | Complete | Independent of topic detection |
| Dual RAG Retrieval | Complete | Embedding + TF-IDF fusion |
| Answer Synthesis | Complete | Natural language, source-cited |
| Persona Extraction | Complete | Per-conversation, evidence-backed |
| React Frontend | Complete | All 4 panels, mobile responsive |
| SQLite Persistence | Complete | Survives server restarts |
| Cloud Deployment | In Progress | Render deployment configured |

---

## How Topic Detection Works

Messages are embedded using `all-MiniLM-L6-v2`. A sliding window of 3
consecutive messages creates a window vector. When the cosine similarity
between two adjacent windows drops below `0.35`, a topic boundary is
recorded and a new `TopicSegment` is created.

For conversations under 6 messages, TF-IDF vectors are computed for the
first and second halves. A cosine distance above `0.5` signals a topic
shift.

## How Retrieval Works

Every user query runs through two parallel searches:

1. The query is embedded and compared against all stored segment embeddings
   (cosine similarity, threshold ≥ 0.20, top 5 results)
2. The query is TF-IDF vectorized and compared against all segment text
   (top 5 results)

Results are merged, deduplicated by segment ID, and re-ranked using:
`score = (0.6 × embedding_score) + (0.4 × tfidf_score)`

The top 3 segments are passed to the synthesizer.

## How Persona Is Built

Persona extraction runs on a single `conversation_id` — never across
multiple conversations. Only User 1's messages are analyzed.

- **Habits**: keyword patterns must appear 3+ times to be recorded
- **Occupation**: only matched against a curated list of 50 known job titles
- **Traits**: computed from ratios (question_ratio > 0.4 = curious,
  exclamation_ratio > 0.3 = expressive, humor signals > 0.1 = humorous)
- **Every field** includes an `evidence` array of direct message quotes

---

## Contributors

| Name | Role |
|---|---|
| Santanu | Project Lead, Architecture, Backend |

---

## License

This project is licensed under the MIT License.

---

<div align="center">
Built with Python, Flask, React, and sentence-transformers · Zero paid APIs
</div>
