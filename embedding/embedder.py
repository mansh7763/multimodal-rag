"""BGE text embeddings and CLIP image embeddings."""

import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor

from config import settings


class TextEmbedder:
    """BGE-small text embeddings for chunks and queries."""

    def __init__(self):
        self.model = SentenceTransformer(settings.text_embedding_model)
        self.model.eval()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of float vectors."""
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                batch_size=64,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query."""
        with torch.no_grad():
            embedding = self.model.encode(
                query,
                normalize_embeddings=True,
            )
        return embedding.tolist()


class ImageEmbedder:
    """CLIP image embeddings for visual content."""

    def __init__(self):
        self.model = CLIPModel.from_pretrained(settings.clip_model)
        self.processor = CLIPProcessor.from_pretrained(settings.clip_model)
        self.model.eval()

    def embed_images(self, images: list[Image.Image]) -> list[list[float]]:
        """Embed a batch of PIL images. Returns list of float vectors."""
        with torch.no_grad():
            inputs = self.processor(images=images, return_tensors="pt", padding=True)
            outputs = self.model.get_image_features(**inputs)
            # Normalize
            outputs = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
        return outputs.tolist()

    def embed_image(self, image: Image.Image) -> list[float]:
        """Embed a single image."""
        return self.embed_images([image])[0]

    def embed_text_for_image_search(self, text: str) -> list[float]:
        """Embed text using CLIP text encoder (for text-to-image search)."""
        with torch.no_grad():
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            outputs = self.model.get_text_features(**inputs)
            outputs = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
        return outputs[0].tolist()


# Singletons — initialized lazily
_text_embedder: TextEmbedder | None = None
_image_embedder: ImageEmbedder | None = None


def get_text_embedder() -> TextEmbedder:
    global _text_embedder
    if _text_embedder is None:
        _text_embedder = TextEmbedder()
    return _text_embedder


def get_image_embedder() -> ImageEmbedder:
    global _image_embedder
    if _image_embedder is None:
        _image_embedder = ImageEmbedder()
    return _image_embedder
