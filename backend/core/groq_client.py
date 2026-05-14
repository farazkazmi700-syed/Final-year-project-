"""
backend/core/groq_client.py
===========================
LLaMA 3 inference via Groq Cloud API (free tier).
FR4: LLaMA 3 Model Integration.

Why Groq instead of running locally?
  - No GPU required
  - Free API (https://console.groq.com — no credit card)
  - Extremely fast inference (GroqChip hardware)
  - Same LLaMA 3 model weights

Setup:
  1. Go to https://console.groq.com
  2. Sign up → API Keys → Create API Key
  3. Add GROQ_API_KEY=gsk_... to your .env file
"""

from groq import Groq
from typing import List, Dict
from backend.config import Config


# ── System Prompt ─────────────────────────────────────────────────────────────
# This instruction is injected at the start of every conversation
SYSTEM_PROMPT = (
    "You are a helpful, friendly, and knowledgeable AI assistant. "
    "Provide clear, accurate, and concise responses. "
    "If you are unsure about something, be honest about it. "
    "Keep your responses focused and easy to understand."
)

# ── Groq Client (created once, reused) ───────────────────────────────────────
_client: Groq = None


def _get_client() -> Groq:
    """
    Lazy-initialize the Groq client.
    Returns a shared instance (singleton pattern).
    """
    global _client
    if _client is None:
        if not Config.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com and add it to .env"
            )
        _client = Groq(api_key=Config.GROQ_API_KEY)
    return _client


def generate_response(
    conversation_history: List[Dict[str, str]],
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """
    Send the full multi-turn conversation to LLaMA 3 and get a response.
    This is the core AI inference function (FR4).

    Multi-turn context: The full conversation history is sent with every
    request so LLaMA 3 can refer back to earlier messages.

    Args:
        conversation_history: List of {"role": "user"/"assistant", "content": "..."}
                               Pass the COMPLETE history, not just the latest message.
        system_prompt:        Optional override for the system instruction.

    Returns:
        The model's text response as a string.

    Raises:
        ValueError:    If GROQ_API_KEY is missing.
        RuntimeError:  If the API call fails.
    """
    client = _get_client()

    # Prepend the system prompt to give the model its persona
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        response = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=messages,
            max_tokens=1024,        # Max length of the response
            temperature=0.7,        # 0=deterministic, 1=creative
            top_p=0.9,
            stream=False,
        )
        return response.choices[0].message.content

    except Exception as e:
        error_msg = str(e)

        # Friendly error messages for common issues
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            raise RuntimeError(
                "Invalid Groq API key. Please check GROQ_API_KEY in your .env file."
            )
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            raise RuntimeError(
                "Groq rate limit reached. Please wait a moment and try again. "
                "(Free tier: 30 requests/minute)"
            )
        if "model_not_found" in error_msg.lower():
            raise RuntimeError(
                f"Model '{Config.GROQ_MODEL}' not found. "
                "Try changing GROQ_MODEL to 'llama3-8b-8192' in .env"
            )
        raise RuntimeError(f"Groq API error: {error_msg}")


def check_groq_connection() -> dict:
    """
    Test the Groq API connection with a minimal request.
    Used by the health-check endpoint.

    Returns:
        {"status": "ok", "model": "..."} or {"status": "error", "message": "..."}
    """
    try:
        response = generate_response(
            [{"role": "user", "content": "Reply with only the word: OK"}]
        )
        return {"status": "ok", "model": Config.GROQ_MODEL, "test_response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}
