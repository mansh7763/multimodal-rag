"""Set up Qdrant collection and load chunks with embeddings."""

import json
from pathlib import Path
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)
from tqdm import tqdm

from config import settings
from embedding.embedder import get_text_embedder


def get_qdrant_client() -> QdrantClient:
    """Create a Qdrant client."""
    if settings.qdrant_api_key:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=120,
        )
    return QdrantClient(url=settings.qdrant_url, timeout=120)


def create_collection(client: QdrantClient) -> None:
    """Create the hf_courses collection with named vectors."""
    collections = [c.name for c in client.get_collections().collections]

    if settings.collection_name in collections:
        print(f"Collection '{settings.collection_name}' already exists. Skipping creation.")
        return

    client.create_collection(
        collection_name=settings.collection_name,
        vectors_config={
            "text": VectorParams(
                size=settings.text_embedding_dim,
                distance=Distance.COSINE,
            ),
            "image": VectorParams(
                size=settings.image_embedding_dim,
                distance=Distance.COSINE,
            ),
        },
    )
    print(f"Created collection '{settings.collection_name}'")


def load_chunks(chunks_path: str = "data/chunks/all_chunks.json") -> list[dict]:
    """Load chunks from JSON file."""
    with open(chunks_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_text_chunks(
    client: QdrantClient,
    chunks: list[dict],
    batch_size: int = 16,
) -> None:
    """Embed and upsert text chunks into Qdrant."""
    embedder = get_text_embedder()

    print(f"Ingesting {len(chunks)} text chunks...")

    for i in tqdm(range(0, len(chunks), batch_size), desc="Ingesting"):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        embeddings = embedder.embed_texts(texts)

        points = []
        for chunk, embedding in zip(batch, embeddings):
            point = PointStruct(
                id=str(uuid4()),
                vector={"text": embedding},
                payload={
                    "content": chunk["content"],
                    "course": chunk["metadata"]["course"],
                    "chapter": chunk["metadata"]["chapter"],
                    "section": chunk["metadata"]["section"],
                    "url": chunk["metadata"]["url"],
                    "content_type": chunk["metadata"]["content_type"],
                    "has_code": chunk["metadata"]["has_code"],
                    "has_image": chunk["metadata"]["has_image"],
                    "image_srcs": chunk["metadata"].get("image_srcs", []),
                },
            )
            points.append(point)

        client.upsert(
            collection_name=settings.collection_name,
            points=points,
        )

    print(f"Ingested {len(chunks)} chunks into Qdrant")


def run_ingestion(chunks_path: str = "data/chunks/all_chunks.json") -> None:
    """Full ingestion pipeline: create collection + embed + upsert."""
    client = get_qdrant_client()
    create_collection(client)

    chunks = load_chunks(chunks_path)
    ingest_text_chunks(client, chunks)

    # Print stats
    info = client.get_collection(settings.collection_name)
    print(f"Collection stats: {info.points_count} points")


if __name__ == "__main__":
    run_ingestion()
