"""Conversation memory and query rewriting."""

from google import genai
from google.genai import types as genai_types

from config import settings


class ConversationMemory:
    """Stores conversation history per session."""

    def __init__(self, max_turns: int | None = None):
        self.max_turns = max_turns or settings.max_history_turns
        self.history: list[dict] = []

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})
        self._trim()

    def get_history(self) -> list[dict]:
        return self.history.copy()

    def clear(self) -> None:
        self.history = []

    def _trim(self) -> None:
        """Keep only the last max_turns pairs (user + assistant)."""
        max_messages = self.max_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]


REWRITE_PROMPT = """You are a query rewriter for a RAG system. Given the conversation history and a follow-up question, rewrite the follow-up into a standalone question that can be understood without the conversation context.

Rules:
- If the question is already standalone, return it as-is
- Replace pronouns (it, they, this) with the actual entity from history
- Keep the rewritten query concise
- Return ONLY the rewritten query, nothing else

Conversation history:
{history}

Follow-up question: {query}

Rewritten standalone query:"""


async def rewrite_query(
    query: str,
    history: list[dict],
) -> str:
    """Rewrite a follow-up query into a standalone query using conversation history.

    If no history exists, returns the query as-is.
    """
    if not history:
        return query

    # Format history for the prompt
    history_text = "\n".join(
        f"{turn['role'].capitalize()}: {turn['content']}" for turn in history
    )
    prompt = REWRITE_PROMPT.format(history=history_text, query=query)

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=256,
            ),
        )
        rewritten = response.text.strip()
        return rewritten if rewritten else query
    except Exception as e:
        print(f"Query rewrite failed: {e}, using original query")
        return query
