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

## 📖 Overview

Most RAG systems treat documents as static text blobs. Real conversations
are different — they evolve over time, shift between topics, and reveal
personality through patterns of language.

ConvoLens was built to solve a specific real-world problem: given a massive CSV of
WhatsApp-style conversations (191,592 messages across 11,001 conversations),
how do you build a system that can answer natural language questions about
the data intelligently — without hallucinating, without dumping raw text,
and without relying on any paid external APIs?

The core idea behind the solution is a three-part pipeline:
1. **Chronological topic segmentation** — detect when conversations shift topic and build summaries of each segment independently.
2. **Grounded persona extraction** — extract habits, traits, facts, and communication style from individual conversations with real message evidence.
3. **Dual-index RAG retrieval** — fuse semantic embedding search with TF-IDF keyword search to find the most relevant context, then synthesize a natural language answer.

---

## ✨ Key Features

The capabilities of the system are categorized into the following logical groups:

### 🧠 Intelligent Processing Engine
- **Stream-based CSV parsing:** Processes 191K+ messages row by row with zero memory overflow. Pure Python `csv` module writing to SQLite in real-time.
- **Chronological ordering guaranteed:** Every message is processed in strict temporal sequence before any analysis begins.
- **SQLite persistence:** The initial processing run happens exactly once. Subsequent server starts load from the database instantly.

### 🔍 Topic & Time Detection System
- **Sliding window topic detection:** Embeds 3 consecutive messages. When cosine similarity drops below 0.35, a topic boundary is recorded.
- **Short conversation fallback:** Conversations under 6 messages use a TF-IDF keyword-shift heuristic.
- **Segment summaries:** Each topic segment gets a label (top 3 TF-IDF keywords) and an extractive summary.
- **100-Message Time Checkpoints:** Independent summary checkpoints are created for every 100 messages chronologically.

### 🕵️ Per-Conversation Persona Extraction
Persona is scoped strictly to a single conversation — never aggregated across multiple conversations. Every field includes an `evidence` array with direct message quotes.
- **Habits:** Sleep patterns, food, routines (requires 3+ occurrences).
- **Personal facts:** Relationships, location, occupation (matched against curated 50-title list).
- **Personality traits:** Curious, expressive, humorous (computed from message ratios).
- **Communication style:** Avg word count, emoji rate, tone.

### 🤖 Dual-Index RAG Retrieval & Synthesis
- **Embedding index:** `all-MiniLM-L6-v2` encodes all segment summaries.
- **TF-IDF index:** `sklearn` TfidfVectorizer indexes full segment text.
- **Fusion scoring:** `final_score = (0.6 × embedding_score) + (0.4 × tfidf_score)`
- **Answer Synthesis:** Generates a grounded natural language answer. Raw context dumps are never shown.

---

## 🏗️ System Architecture

The following diagram conceptually explains how different components interact and the internal workflow:

```text
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

## 💻 Tech Stack

### Backend Software Layer
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Core runtime |
| Flask | 3.1.1 | REST API server (factory pattern) |
| Flask-CORS | 5.0.1 | Cross-origin request handling |
| sentence-transformers | 3.0+ | Semantic embeddings (all-MiniLM-L6-v2) |
| scikit-learn | 1.4+ | TF-IDF vectorization |
| numpy & scipy | 1.26+ | Vector math and cosine similarity |
| SQLite3 | built-in | Persistent storage |

### Frontend Software Layer
| Technology | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| Vite | 6 | Build tool and dev server |
| JavaScript (ES2022) | — | Language (no TypeScript) |
| CSS Custom Properties | — | Theming and dark mode |
| Context + useReducer | — | State management (no Redux) |

### Infrastructure Layer
| Technology | Purpose |
|---|---|
| Docker | Containerized builds |
| Render | Cloud deployment (free tier) |
| GitHub Actions | CI/CD pipeline |

---

## 🚀 Setup and Installation

Follow these step-by-step instructions to run the project without ambiguity.

**Prerequisites:**
- Python 3.11+
- Node.js 18+
- Git

**1. Clone the repository**
```bash
git clone https://github.com/santanu949/Convolens.git
cd Convolens
```

**2. Add your dataset**
Place your `conversations.csv` file at `backend/data/conversations.csv`.
*(The CSV should have one conversation per row, with messages separated by line breaks within each quoted cell.)*

**3. Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**4. Install frontend dependencies**
```bash
cd frontend
npm install
```

**5. Start the backend**
```bash
cd backend
python app.py
```
*On first run with an empty database, processing starts automatically. It takes 5–15 minutes.*

**6. Start the frontend**
In a second terminal:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🎮 Usage Guide

Here is how the system operates from a user's perspective:

- **Chat Panel:** Type any natural language question (e.g., `"What kind of person is this user?"`, `"What topics do they discuss most?"`). The system retrieves relevant topic segments and generates a grounded answer with source citations.
- **Topics Panel:** Browse all detected topic segments in chronological order with extracted summaries.
- **Persona Panel:** Select any conversation from the dropdown to view extracted habits, personal facts, personality traits, and communication style statistics with exact quote evidence.
- **Checkpoints Panel:** Browse time-based summaries created every 100 messages, independent of topic boundaries.

---

## 📁 Project Structure

```text
Convolens/
├── backend/
│   ├── api/           # HTTP routes and middleware
│   ├── services/      # Processor, retriever, synthesizer, persona logic
│   ├── core/          # Stream parser, topic detector, checkpoints
│   ├── models/        # Dataclasses (message, segment, persona_model)
│   ├── storage/       # SQLite db and Numpy vector_store
│   ├── data/          # Local CSV and SQLite DB storage
│   ├── app.py         # Flask factory entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/# React UI components (Panels, Sidebar, etc.)
│   │   ├── hooks/     # Custom React hooks (useChat, useProcessing)
│   │   ├── services/  # API fetch wrappers
│   │   └── store/     # React Context + useReducer state
│   ├── package.json
│   └── vite.config.js
├── Dockerfile
├── docker-compose.yml
└── render.yaml
```

---

## 📊 Current Status

| Component | Status | Notes |
|---|---|---|
| System Architecture | Complete | Strict layered separation |
| CSV Stream Parser | Complete | 191K messages, zero OOM |
| Topic Detection | Complete | Window=3, cosine threshold=0.35 |
| Dual RAG Retrieval | Complete | Embedding + TF-IDF fusion |
| Persona Extraction | Complete | Per-conversation, evidence-backed |
| React Frontend | Complete | All 4 panels, mobile responsive |
| Cloud Deployment | In Progress | Render deployment configured |

---

## 👥 Contributors

| Name | Role |
|---|---|
| Santanu | Project Lead, Architecture, Backend |

---

## 📄 License

This project is licensed under the MIT License.
