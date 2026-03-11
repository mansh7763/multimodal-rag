# HuggingFace Learn Multimodal RAG System

## Project Vision

Build a **multimodal Retrieval-Augmented Generation (RAG) system** over the entire **Hugging Face Learn ecosystem** that enables users to ask questions about course content — including text, code, and images — and receive answers grounded in the official learning material with citations.

Example:

> **User Query:** How does LoRA work in fine-tuning LLMs?
>
> **Answer:** LoRA (Low-Rank Adaptation) reduces the number of trainable parameters by injecting low-rank matrices into attention layers...
>
> **Source:** [Hugging Face LLM Course → Chapter 7 → Parameter-Efficient Fine-Tuning](https://huggingface.co/learn/llm-course/chapter7/peft)

---

# Table of Contents

1. Problem Definition
2. Dataset Scope
3. System Architecture
4. Data Scraping Pipeline
5. Data Processing and Chunking
6. Storage Design
7. Embedding and Indexing
8. Multimodal Image Pipeline
9. Retrieval System
10. Context Construction
11. Conversational Memory and Query Rewriting
12. Generation Layer
13. Evaluation Framework
14. Deployment Architecture
15. Folder Structure
16. Final Deliverables

---

# 1. Problem Definition

Modern learning platforms contain high-quality structured knowledge but searching them efficiently is difficult.

Traditional keyword search fails to:

- Understand semantic meaning
- Connect related sections across courses
- Answer conceptual questions
- Handle visual content (diagrams, architecture figures)
- Reference multiple sections

This project builds a **multimodal** semantic knowledge assistant over Hugging Face courses using Retrieval-Augmented Generation.

---

# 2. Dataset Scope

The system will ingest the entire Hugging Face Learn portal.

Target courses:

- LLM Course
- Audio Course
- Smol Course
- Diffusion Course
- Transformers Course
- Reinforcement Learning Course

Estimated scale:

- Documents: 500–800 pages
- Text chunks: 50k–120k
- Images: 2k–5k (diagrams, architecture figures, plots)

---

# 3. System Architecture

```
Scraping → Parse HTML → Chunk (text + code + images)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              BGE embedding       CLIP embedding
              (text chunks)       (image chunks)
                    │                   │
                    └─────────┬─────────┘
                              ▼
                     Qdrant (single collection, named vectors)
                              │
                              ▼
              User query → BGE + CLIP search
                              │
                              ▼
                     Merge text + image results
                              │
                              ▼
                     Gemini 2.5 (sees images + text)
                              │
                              ▼
                     Answer with citations + images
```

---

# 4. Data Scraping Pipeline

Strategy:

1. Crawl course index pages to discover all module URLs
2. Download HTML pages
3. Parse structured content (headings, paragraphs, code blocks, images, tables)
4. Download and store images locally
5. Preserve course → chapter → section hierarchy

Tools:

- Playwright (for JS-rendered pages)
- BeautifulSoup (HTML parsing)
- Requests (static pages)

---

# 5. Data Processing and Chunking

## Chunking Strategy: Semantic Chunking by Document Structure

Use HTML heading structure (h2/h3) as natural chunk boundaries:

```
Page HTML
  → Split by headings (h2/h3)
    → Each section becomes a chunk
      → If section > 500 tokens, split at paragraph boundaries
      → If section < 100 tokens, merge with next section
```

## Chunk format:

Each chunk carries a **hierarchical prefix** in the content itself so the embedding captures context:

```json
{
  "content": "LLM Course > Chapter 3 > Attention Mechanism\n\nThe attention mechanism allows the model to focus on relevant parts of the input sequence...",
  "metadata": {
    "course": "llm-course",
    "chapter": "chapter-3",
    "section": "attention-mechanism",
    "url": "https://huggingface.co/learn/llm-course/chapter3/attention",
    "content_type": "text",
    "has_code": true,
    "has_image": false
  }
}
```

## Rules:

- **Code blocks:** Keep code together with its preceding explanation as one chunk
- **Long code blocks (>30 lines):** Chunk separately with explanation as context prefix
- **Tables:** Convert HTML tables to markdown, embed as text chunks
- **Images:** Handled separately in the multimodal pipeline (Section 8)

---

# 6. Storage Design

## Single Qdrant Collection with Named Vectors

No PostgreSQL needed. Qdrant stores vectors + payload metadata.

```python
client.create_collection(
    collection_name="hf_courses",
    vectors_config={
        "text": VectorParams(size=384, distance=Distance.COSINE),   # BGE
        "image": VectorParams(size=512, distance=Distance.COSINE),  # CLIP
    },
)
```

Each chunk payload stores:

- course, chapter, section
- content (text)
- content_type ("text" | "code" | "image" | "table")
- url (clickable link to source)
- image_url (for image chunks)
- caption (AI-generated description for image chunks)

Use metadata filtering for course-specific queries:

```python
query_filter={"must": [{"key": "course", "value": "llm-course"}]}
```

---

# 7. Embeddings

- **Text + Code:** `BAAI/bge-small-en-v1.5` (384 dims) — lightweight, strong quality
- **Images:** `openai/clip-vit-base-patch32` (512 dims) — visual similarity search

Single embedding model for all text (no separate CodeBERT needed — code with surrounding explanation embeds well).

---

# 8. Multimodal Image Pipeline

This is what makes the project truly multimodal.

## During Ingestion:

1. Scrape images from course pages along with surrounding context
2. Generate captions using Gemini 2.5 Flash: "Describe this technical diagram in detail, including labels, axes, and relationships shown"
3. Store per image chunk:
   - CLIP embedding of the image → `image` vector
   - BGE embedding of the caption → `text` vector
   - Image URL + caption in payload

## Multimodal Search Paths:

| Path | Example |
|------|---------|
| **Text → Text** | "How does LoRA work?" → finds text explanations |
| **Text → Image** | "Show me the transformer architecture" → finds diagrams |
| **Image → Image** | User uploads a diagram → finds similar ones |
| **Image → Text** | User uploads a screenshot → finds relevant explanation |

---

# 9. Retrieval System

Dense vector search via Qdrant HNSW index (approximate nearest neighbor, O(log n)).

Start with dense-only retrieval. Add BM25 hybrid search later only if retrieval quality is insufficient.

```python
# Text search
text_results = client.query_points(
    collection_name="hf_courses",
    query=query_embedding,      # BGE embedding of user query
    using="text",               # search text vector space
    limit=10,
)

# Image search (when query asks for visual content)
image_results = client.query_points(
    collection_name="hf_courses",
    query=query_clip_embedding,  # CLIP embedding of user query
    using="image",               # search image vector space
    limit=5,
)
```

Merge text + image results, deduplicate by section.

**Reranking:** Not included in v1. Add cross-encoder reranker (bge-reranker-large) only if retrieval precision is low after evaluation.

---

# 10. Context Construction

Combine retrieved chunks into a prompt context:

- Explanation text
- Code blocks (with language tags)
- Image URLs + captions (Gemini 2.5 can see images natively)
- Table content (as markdown)
- Source citations for each chunk

---

# 11. Conversational Memory and Query Rewriting

## Conversational Memory:

Store last 5 conversation turns. Inject into the generation prompt:

```
Previous conversation:
User: What is LoRA?
Assistant: LoRA is... [from Chapter 7]

Current question: How is it different from full fine-tuning?
```

## Query Rewriting:

Before retrieval, use the LLM to rewrite vague follow-up queries into standalone queries:

- "How is it different?" → "How is LoRA different from full fine-tuning?"
- "Show me a diagram" → "Show me a diagram of LoRA architecture from the PEFT section"

This dramatically improves retrieval on conversational queries.

---

# 12. Generation Layer

## LLM Models:

- **Primary:** Gemini 2.5 (multimodal — can see retrieved images + text)
- **Fallback:** Llama 3.3 70B via Groq API (text-only, fast)

Fallback triggers when: Gemini API is down, rate limited, or times out.

## Prompt Design:

Instruct the model to:

- Answer based only on retrieved context
- Cite the course, chapter, and section for every claim
- Include clickable source URLs
- Reference relevant images/diagrams when available
- Say "I couldn't find this in the courses" when context is insufficient

---

# 13. Evaluation Framework

## Hand-Curated Test Set (Priority):

Build 50 Q&A pairs manually from the courses. This is more valuable than synthetic evaluation.

Categories:
- Factual questions (single-section answer)
- Cross-section questions (requires multiple chunks)
- Visual questions ("What does the transformer architecture look like?")
- Follow-up questions (tests conversational memory)

## Metrics:

Retrieval:
- Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)

Generation:
- Faithfulness (does the answer match the source?)
- Correctness (is the answer right?)
- Citation accuracy (do the citations point to the right sections?)

## Tools:

- RAGAS for automated evaluation
- Manual review for the 50-pair test set

---

# 14. Deployment Architecture

```
User → Next.js / Streamlit frontend
  → FastAPI backend
    → Qdrant Cloud (single collection, named vectors)
    → Gemini 2.5 API (primary generation)
    → Groq API (fallback generation)
```

- **Backend:** FastAPI with streaming responses (SSE)
- **Vector DB:** Qdrant Cloud (free tier)
- **Frontend:** Streamlit for MVP, Next.js for production
- **Hosting:** Railway or Render for backend
- **Containerization:** Docker

No self-hosted vLLM, no Prometheus/Grafana. Add monitoring after getting users.

---

# 15. Folder Structure

```
hf-course-rag/
├── scraper/          # Crawling and HTML downloading
├── parser/           # HTML parsing, chunking, table/code extraction
├── images/           # Image pipeline: download, caption, CLIP embedding
├── ingestion/        # Qdrant collection setup and data loading
├── embedding/        # BGE + CLIP embedding logic
├── retrieval/        # Search, merge, and ranking logic
├── generation/       # LLM prompting, streaming, fallback chain
├── memory/           # Conversational memory and query rewriting
├── evaluation/       # Test set, metrics, RAGAS integration
├── backend/          # FastAPI app
├── frontend/         # Streamlit / Next.js
├── data/             # Raw scraped data, processed chunks
│   ├── raw_html/
│   ├── chunks/
│   └── images/
├── deployment/       # Dockerfiles, configs
├── .env.example      # API key template
└── README.md
```

---

# 16. Final Deliverables

- Multimodal HuggingFace Course Assistant (live demo URL)
- Structured dataset with text + image chunks
- Dense retrieval pipeline with multimodal search
- Hand-curated evaluation benchmark (50 Q&A pairs)
- Conversational interface with memory
- Documentation of failure modes and limitations
