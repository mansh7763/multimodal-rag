"""FastAPI backend for the HuggingFace Course RAG system."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import settings
from generation.llm import generate_answer
from ingestion.ingest import get_qdrant_client
from memory.conversation import ConversationMemory, rewrite_query
from retrieval.search import search_multimodal


# Store active conversation sessions
sessions: dict[str, ConversationMemory] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify Qdrant connection
    try:
        client = get_qdrant_client()
        info = client.get_collection(settings.collection_name)
        print(f"Connected to Qdrant. Collection has {info.points_count} points.")
    except Exception as e:
        print(f"Warning: Could not connect to Qdrant: {e}")
    yield
    # Shutdown: cleanup
    sessions.clear()


app = FastAPI(
    title="HuggingFace Course RAG",
    description="Multimodal RAG system over HuggingFace Learn courses",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"
    course_filter: str | None = None
    include_images: bool = True


class SourceResult(BaseModel):
    content: str
    course: str
    chapter: str
    section: str
    url: str
    score: float
    content_type: str
    image_srcs: list[str] = []


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceResult]
    rewritten_query: str | None = None


def _get_session(session_id: str) -> ConversationMemory:
    if session_id not in sessions:
        sessions[session_id] = ConversationMemory()
    return sessions[session_id]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Non-streaming query endpoint. Returns full answer + sources."""
    session = _get_session(request.session_id)
    history = session.get_history()

    # Rewrite query if there's conversation history
    rewritten = await rewrite_query(request.query, history)

    # Retrieve
    results = search_multimodal(
        query=rewritten,
        course_filter=request.course_filter,
        include_images=request.include_images,
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No relevant content found in the courses.",
        )

    # Generate (collect full response)
    answer_parts = []
    async for token in generate_answer(rewritten, results, history):
        answer_parts.append(token)
    answer = "".join(answer_parts)

    # Update conversation memory
    session.add_user_message(request.query)
    session.add_assistant_message(answer)

    sources = [
        SourceResult(
            content=r["content"][:300],
            course=r["course"],
            chapter=r["chapter"],
            section=r["section"],
            url=r["url"],
            score=r["score"],
            content_type=r["content_type"],
            image_srcs=r.get("image_srcs", []),
        )
        for r in results[:5]
    ]

    return QueryResponse(
        answer=answer,
        sources=sources,
        rewritten_query=rewritten if rewritten != request.query else None,
    )


@app.post("/query/stream")
async def query_stream_endpoint(request: QueryRequest):
    """Streaming query endpoint. Returns SSE events."""
    session = _get_session(request.session_id)
    history = session.get_history()

    rewritten = await rewrite_query(request.query, history)

    results = search_multimodal(
        query=rewritten,
        course_filter=request.course_filter,
        include_images=request.include_images,
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No relevant content found in the courses.",
        )

    async def event_generator():
        # Send sources first
        import json

        sources = [
            {
                "content": r["content"][:300],
                "course": r["course"],
                "chapter": r["chapter"],
                "section": r["section"],
                "url": r["url"],
                "score": r["score"],
                "image_srcs": r.get("image_srcs", []),
            }
            for r in results[:5]
        ]
        yield {"event": "sources", "data": json.dumps(sources)}

        if rewritten != request.query:
            yield {"event": "rewrite", "data": rewritten}

        # Stream answer tokens
        full_answer = []
        async for token in generate_answer(rewritten, results, history):
            full_answer.append(token)
            yield {"event": "token", "data": token}

        # Update memory after full response
        answer = "".join(full_answer)
        session.add_user_message(request.query)
        session.add_assistant_message(answer)

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@app.get("/courses")
async def list_courses():
    """List available courses in the collection."""
    from scraper.crawler import COURSES

    return {"courses": list(COURSES.keys())}


@app.post("/session/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    if session_id in sessions:
        sessions[session_id].clear()
    return {"status": "cleared"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        client = get_qdrant_client()
        info = client.get_collection(settings.collection_name)
        return {
            "status": "healthy",
            "qdrant": "connected",
            "points": info.points_count,
        }
    except Exception as e:
        return {"status": "degraded", "qdrant": str(e)}
