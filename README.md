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

## Demo

- **Frontend:** Deployed on Vercel
- **Backend API:** Deployed on HuggingFace Spaces

## Features

- **Multimodal Search** — Dense retrieval over text and image embeddings using Qdrant
- **Streaming Answers** — Real-time token streaming via Server-Sent Events (SSE)
- **Source Citations** — Every answer links back to the exact course, chapter, and section
- **Conversational Memory** — Follow-up questions are rewritten into standalone queries using conversation history
- **Course Filtering** — Scope your search to a specific course
- **LLM Fallback** — Gemini 2.5 Flash as primary, Groq Llama 3.3 70B as fallback

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
Scraper → Parser → Chunker → BGE + CLIP embeddings → Qdrant Cloud
                                                         │
User → Next.js Frontend → FastAPI Backend → Query Rewrite
                                │
                          Dense Search (text + image vectors)
                                │
                          Merge Results → Gemini 2.5 Flash → Streamed Answer with Citations
```

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI with SSE streaming
- Qdrant Cloud (vector database)
- Sentence-Transformers (`BAAI/bge-small-en-v1.5` for text, 384 dims)
- CLIP (`openai/clip-vit-base-patch32` for images, 512 dims)
- Google Gemini 2.5 Flash (primary LLM)
- Groq Llama 3.3 70B (fallback LLM)

**Frontend:**
- Next.js 16 with TypeScript
- Tailwind CSS v4
- React 19

## Project Structure

```
├── scraper/          # Course content fetching from GitHub repos
├── parser/           # Markdown chunking by heading structure
├── embedding/        # BGE (text) + CLIP (image) embedding logic
├── ingestion/        # Qdrant collection setup and data loading
├── retrieval/        # Multimodal search and result merging
├── generation/       # LLM prompting, streaming, fallback chain
├── memory/           # Conversation history and query rewriting
├── backend/          # FastAPI application
├── frontend/         # Next.js chat interface
├── evaluation/       # Test set and metrics
├── data/             # Raw scraped content and processed chunks
├── config.py         # Centralized settings via pydantic-settings
├── run.py            # Uvicorn entry point
├── Dockerfile        # HuggingFace Spaces deployment
└── requirements.txt  # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Qdrant Cloud account (free tier)
- Gemini API key
- Groq API key

### 1. Clone the repo

```bash
git clone https://github.com/mansh7763/multimodal-rag.git
cd multimodal-rag
```

### 2. Set up environment

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
# Scrape courses
python -m scraper.crawler

# Parse and chunk
python -m parser.chunker

# Embed and load into Qdrant
python -m ingestion.ingest
```

### 5. Run the backend

```bash
python run.py
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

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
| POST | `/query` | Non-streaming query, returns full answer + sources |
| POST | `/query/stream` | Streaming query via SSE |
| GET | `/courses` | List indexed courses |
| POST | `/session/{id}/clear` | Clear conversation history |
| GET | `/health` | Health check with Qdrant status |

## Deployment

**Backend** is deployed on HuggingFace Spaces using Docker SDK.

**Frontend** is deployed on Vercel with `NEXT_PUBLIC_BACKEND_URL` pointing to the HF Spaces URL.

## License

MIT
