---
title: HuggingFace Course RAG API
emoji: 🤗
colorFrom: yellow
colorTo: purple
sdk: docker
app_port: 7860
---

# HuggingFace Course RAG

A multimodal Retrieval-Augmented Generation system over the [Hugging Face Learn](https://huggingface.co/learn) ecosystem. Ask questions about course content — text, code, and images — and get cited answers grounded in the official learning material.



## Features

- **Multimodal Search** — Dense retrieval over text and image embeddings using Qdrant
- **Real-time Streaming** — Token-by-token answer streaming via Server-Sent Events (SSE)
- **Numbered Citations** — Every claim is backed by short clickable references (e.g. [1], [2]) linking to the original course material
- **Conversational Memory** — Follow-up questions are automatically rewritten into standalone queries using conversation history
- **Course Filtering** — Scope your search to a specific course via filter pills
- **LLM Fallback** — Gemini 2.5 Flash as primary, Groq Llama 3.3 70B as automatic fallback

## Courses Indexed

| Course | Source |
|--------|--------|
| Agents Course | huggingface/agents-course |
| Smol Course | huggingface/smol-course |
| Deep RL Course | huggingface/deep-rl-class |
| Audio Course | huggingface/audio-transformers-course |
| NLP Course | huggingface/course |
| Diffusion Course | huggingface/diffusion-models-class |
| LLM Course | huggingface/llm-course |
| Transformers Course | huggingface/transformers-course |

## Architecture

```
┌─────────────────────── Ingestion Pipeline ───────────────────────┐
│                                                                  │
│  Scraper (GitHub) → Parser (Markdown) → Semantic Chunker         │
│                                          │                       │
│                               ┌──────────┴──────────┐           │
│                               ▼                     ▼           │
│                        BGE Embeddings         CLIP Embeddings    │
│                        (text, 384d)          (images, 512d)      │
│                               └──────────┬──────────┘           │
│                                          ▼                       │
│                                    Qdrant Cloud                  │
│                              (single collection,                 │
│                               named vectors)                     │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────── Query Pipeline ───────────────────────────┐
│                                                                  │
│  User → Next.js Frontend (Vercel)                                │
│              │                                                   │
│              ▼                                                   │
│         FastAPI Backend (HF Spaces)                              │
│              │                                                   │
│         Query Rewrite (conversation-aware)                       │
│              │                                                   │
│         Dense Search (BGE text + CLIP image vectors)             │
│              │                                                   │
│         Merge & Deduplicate Results                              │
│              │                                                   │
│         Gemini 2.5 Flash (or Groq fallback)                      │
│              │                                                   │
│         SSE Stream → Cited Answer with [1], [2] references       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, SSE streaming (sse-starlette), Pydantic |
| Vector DB | Qdrant Cloud (free tier, HNSW index) |
| Text Embeddings | BAAI/bge-small-en-v1.5 (384 dims) |
| Image Embeddings | openai/clip-vit-base-patch32 (512 dims) |
| Primary LLM | Google Gemini 2.5 Flash |
| Fallback LLM | Llama 3.3 70B via Groq API |
| Frontend Hosting | Vercel |
| Backend Hosting | HuggingFace Spaces (Docker) |

## Project Structure

```
├── scraper/          # Course content fetching from GitHub repos
├── parser/           # Markdown chunking by heading structure (h2/h3)
├── embedding/        # BGE (text) + CLIP (image) embedding logic
├── ingestion/        # Qdrant collection setup and data loading
├── retrieval/        # Dense search, merge, and ranking
├── generation/       # LLM prompting, streaming, fallback chain
├── memory/           # Conversation history and query rewriting
├── backend/          # FastAPI application
├── frontend/         # Next.js chat interface
│   ├── app/
│   │   ├── page.tsx              # Main chat page with SSE streaming
│   │   ├── layout.tsx            # Root layout
│   │   ├── globals.css           # Dark theme styles
│   │   └── components/
│   │       ├── ChatMessage.tsx   # Message rendering with markdown + citations
│   │       ├── ChatInput.tsx     # Input with course filter pills
│   │       └── Sidebar.tsx       # Session management
│   ├── next.config.ts
│   ├── vercel.json
│   └── package.json
├── evaluation/       # Test set and metrics
├── data/             # Raw scraped content and processed chunks
├── config.py         # Centralized settings via pydantic-settings
├── run.py            # Uvicorn entry point
├── Dockerfile        # HuggingFace Spaces deployment
├── requirements.txt  # Full Python dependencies
└── requirements-deploy.txt  # Lightweight deploy dependencies (no scraping libs)
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: [Gemini](https://aistudio.google.com/apikey), [Groq](https://console.groq.com/keys), [Qdrant Cloud](https://cloud.qdrant.io/)

### 1. Clone the repo

```bash
git clone https://github.com/mansh7763/multimodal-rag.git
cd multimodal-rag
```

### 2. Set up Python environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
```

### 4. Ingest data

```bash
# Scrape course content from GitHub repos
python -m scraper.crawler

# Parse markdown and chunk by headings
python -m parser.chunker

# Generate embeddings and load into Qdrant
python -m ingestion.ingest
```

### 5. Run the backend

```bash
python run.py
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 6. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| POST | `/query` | Non-streaming query — returns full answer + sources |
| POST | `/query/stream` | Streaming query via SSE — real-time token streaming |
| GET | `/courses` | List all indexed courses |
| POST | `/session/{id}/clear` | Clear conversation history for a session |
| GET | `/health` | Health check with Qdrant connection status |

### Example request

```bash
curl -X POST https://abhiyanta-multimodal-rag.hf.space/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "How does LoRA work?", "session_id": "test"}'
```

## Deployment

### Backend — HuggingFace Spaces

The backend is deployed as a Docker Space on HuggingFace:

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) with **Docker SDK** (Blank template)
2. Add secrets in **Settings > Variables and Secrets**:
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `QDRANT_URL`
   - `QDRANT_API_KEY`
3. Push code to the Space:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
   git push hf master:main
   ```

### Frontend — Vercel

The frontend is deployed on Vercel:

1. Import the GitHub repo at [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `frontend`
3. Add environment variable:
   - `NEXT_PUBLIC_BACKEND_URL` = `https://YOUR_USERNAME-YOUR_SPACE.hf.space`
4. Deploy — Vercel auto-detects Next.js

### After deployment

- Backend API: `https://YOUR_USERNAME-YOUR_SPACE.hf.space`
- Frontend: `https://your-project.vercel.app`
- The HF Spaces free tier may have cold starts (~30s) after inactivity

## License

MIT
