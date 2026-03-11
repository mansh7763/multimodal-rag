# CLAUDE.md — HuggingFace Multimodal RAG Project

Ideas related to this project is clearly mentioned in @hf_course_rag_ideas.md file. Look for it for any clarification.

## Project Overview

Multimodal RAG system over HuggingFace Learn courses. Users ask questions about course content (text, code, images) and get cited answers.

## Key Decisions

- **Single Qdrant collection** with named vectors (`text` + `image`) and metadata filtering by course
- **No PostgreSQL** — Qdrant payloads handle all metadata
- **Primary LLM:** Gemini 2.5 (multimodal) | **Fallback:** Llama 3.3 70B via Groq
- **Text embeddings:** BAAI/bge-small-en-v1.5 (384 dims)
- **Image embeddings:** CLIP vit-base-patch32 (512 dims)
- **No hybrid search in v1** — dense-only, add BM25 later if needed
- **No reranker in v1** — add cross-encoder later if retrieval quality is poor
- **No monitoring stack in v1** — no Prometheus/Grafana/Langfuse until there are users

## Chunking Strategy

- Semantic chunking by HTML heading structure (h2/h3)
- Each chunk carries hierarchical prefix: "Course > Chapter > Section\n\nContent..."
- Code blocks stay with their preceding explanation
- Tables converted to markdown
- Images captioned by Gemini 2.5 Flash during ingestion

## Architecture

```
Scraper → Parser → Chunker → BGE + CLIP embeddings → Qdrant
User → FastAPI → Query rewrite → Dense search (text + image) → Merge → Gemini 2.5 → Streamed answer with citations
```

## Tech Stack

- Python 3.11+
- FastAPI (backend)
- Qdrant (vector DB)
- Playwright + BeautifulSoup (scraping)
- Sentence-Transformers (BGE embeddings)
- transformers (CLIP)
- google-genai (Gemini 2.5)
- groq (Llama 3.3 fallback)
- Next.js (MVP frontend))

## Code Conventions

- Use absolute imports
- Type hints on all function signatures
- Config via .env files (never commit secrets)
- Async FastAPI endpoints with streaming responses (SSE)

## File Structure

- `scraper/` — crawling and HTML download
- `parser/` — HTML parsing, chunking
- `images/` — image download, captioning, CLIP embedding
- `ingestion/` — Qdrant setup and data loading
- `embedding/` — BGE + CLIP logic
- `retrieval/` — search, merge, ranking
- `generation/` — LLM prompting, streaming, fallback
- `memory/` — conversation history, query rewriting
- `evaluation/` — test set, metrics
- `backend/` — FastAPI app
- `frontend/` — UI
- `data/` — raw HTML, processed chunks, images
