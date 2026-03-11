"""Dense retrieval: text search + image search + merge."""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from config import settings
from embedding.embedder import get_text_embedder, get_image_embedder
from ingestion.ingest import get_qdrant_client


def search_text(
    query: str,
    client: QdrantClient | None = None,
    course_filter: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Dense text search using BGE embeddings."""
    client = client or get_qdrant_client()
    embedder = get_text_embedder()
    top_k = top_k or settings.top_k_text

    query_vector = embedder.embed_query(query)

    # Build optional course filter
    query_filter = None
    if course_filter:
        query_filter = Filter(
            must=[FieldCondition(key="course", match=MatchValue(value=course_filter))]
        )

    results = client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        using="text",
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    return [
        {
            "id": str(point.id),
            "score": point.score,
            "content": point.payload["content"],
            "course": point.payload["course"],
            "chapter": point.payload["chapter"],
            "section": point.payload["section"],
            "url": point.payload["url"],
            "content_type": point.payload.get("content_type", "text"),
            "has_image": point.payload.get("has_image", False),
            "image_srcs": point.payload.get("image_srcs", []),
        }
        for point in results.points
    ]


def search_images(
    query: str,
    client: QdrantClient | None = None,
    course_filter: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Search for images using CLIP text-to-image embedding."""
    client = client or get_qdrant_client()
    image_embedder = get_image_embedder()
    top_k = top_k or settings.top_k_image

    query_vector = image_embedder.embed_text_for_image_search(query)

    query_filter = None
    if course_filter:
        query_filter = Filter(
            must=[FieldCondition(key="course", match=MatchValue(value=course_filter))]
        )

    results = client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        using="image",
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    return [
        {
            "id": str(point.id),
            "score": point.score,
            "content": point.payload.get("content", ""),
            "course": point.payload["course"],
            "chapter": point.payload["chapter"],
            "section": point.payload["section"],
            "url": point.payload["url"],
            "content_type": "image",
            "image_srcs": point.payload.get("image_srcs", []),
            "caption": point.payload.get("caption", ""),
        }
        for point in results.points
    ]


def search_multimodal(
    query: str,
    client: QdrantClient | None = None,
    course_filter: str | None = None,
    include_images: bool = True,
) -> list[dict]:
    """Combined text + image search. Merges and deduplicates results."""
    client = client or get_qdrant_client()

    # Always do text search
    text_results = search_text(query, client, course_filter)

    if not include_images:
        return text_results

    # Image search
    try:
        image_results = search_images(query, client, course_filter)
    except Exception:
        # CLIP might not have any image vectors yet
        image_results = []

    # Merge: deduplicate by id, keep higher score
    seen_ids = set()
    merged = []

    for result in text_results:
        seen_ids.add(result["id"])
        merged.append(result)

    for result in image_results:
        if result["id"] not in seen_ids:
            merged.append(result)

    # Sort by score descending
    merged.sort(key=lambda x: x["score"], reverse=True)

    return merged
