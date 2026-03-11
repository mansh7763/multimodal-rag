from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM API keys
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    collection_name: str = "hf_courses"

    # Embedding dimensions
    text_embedding_dim: int = 384
    image_embedding_dim: int = 512

    # Models
    text_embedding_model: str = "BAAI/bge-small-en-v1.5"
    clip_model: str = "openai/clip-vit-base-patch32"
    gemini_model: str = "gemini-2.5-flash"
    groq_model: str = "llama-3.3-70b-versatile"

    # Chunking
    max_chunk_tokens: int = 500
    min_chunk_tokens: int = 100

    # Retrieval
    top_k_text: int = 10
    top_k_image: int = 5

    # Conversation
    max_history_turns: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
