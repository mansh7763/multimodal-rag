"""LLM generation with Gemini primary and Groq fallback."""

from typing import AsyncGenerator

from google import genai
from google.genai import types as genai_types
from groq import AsyncGroq

from config import settings

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about Hugging Face courses.

Rules:
1. Answer ONLY based on the provided context. Do not use outside knowledge.
2. Cite sources using short numbered references like [1], [2], etc. that match the source numbers in the context. Make each reference a clickable link using the URL from that source, e.g. [1](url). You can combine multiple references like [1](url1) [2](url2).
3. If the context includes relevant images or diagrams, mention them in your answer.
4. If the context is insufficient to answer the question, say: "I couldn't find enough information in the Hugging Face courses to answer this question."
5. Be concise and direct. Use code blocks for code examples.
6. If the question is a follow-up, use the conversation history for context."""


def _build_context(results: list[dict]) -> str:
    """Format retrieved results into a context string for the LLM."""
    context_parts = []
    for i, r in enumerate(results, 1):
        source = f"[{r['course']} > {r['chapter']} > {r['section']}]({r['url']})"
        content = r["content"]

        # Include image references if present
        if r.get("image_srcs"):
            images = "\n".join(f"![image]({src})" for src in r["image_srcs"])
            content += f"\n\nRelated images:\n{images}"

        context_parts.append(f"--- Source {i}: {source} ---\n{content}")

    return "\n\n".join(context_parts)


def _build_messages(
    query: str,
    context: str,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build message list for the LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history
    if history:
        for turn in history[-settings.max_history_turns :]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current query with context
    user_message = f"""Context from Hugging Face courses:

{context}

---

Question: {query}"""

    messages.append({"role": "user", "content": user_message})
    return messages


async def generate_gemini(
    query: str,
    results: list[dict],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a response from Gemini 2.5."""
    context = _build_context(results)
    messages = _build_messages(query, context, history)

    client = genai.Client(api_key=settings.gemini_api_key)

    # Convert to Gemini format
    gemini_history = []
    system_instruction = None
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        else:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=msg["content"])],
                )
            )

    response = client.models.generate_content_stream(
        model=settings.gemini_model,
        contents=gemini_history,
        config=genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text


async def generate_groq(
    query: str,
    results: list[dict],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a response from Groq (Llama 3.3) as fallback."""
    context = _build_context(results)
    messages = _build_messages(query, context, history)

    client = AsyncGroq(api_key=settings.groq_api_key)

    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def generate_answer(
    query: str,
    results: list[dict],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Generate with Gemini, fall back to Groq on failure."""
    try:
        async for token in generate_gemini(query, results, history):
            yield token
    except Exception as e:
        print(f"Gemini failed: {e}, falling back to Groq")
        async for token in generate_groq(query, results, history):
            yield token
