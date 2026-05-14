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

from typing import List, Dict

import requests

from backend.config import Config


# ── System Prompt ─────────────────────────────────────────────────────────────
# This instruction is injected at the start of every conversation
SYSTEM_PROMPT = (
    "You are a helpful, friendly, and knowledgeable AI assistant. "
    "Provide clear, accurate, and concise responses. "
    "If you are unsure about something, be honest about it. "
    "Keep your responses focused and easy to understand."
)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


MODEL_ALIASES = {
    # Older Groq model IDs can be unavailable on some accounts.
    # Keep the app working when an old .env is still present.
    "llama3-8b-8192": "llama-3.1-8b-instant",
    "llama3-70b-8192": "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768": "llama-3.1-8b-instant",
}


def _configured_model() -> str:
    """Return a current Groq model ID, accepting old project defaults."""
    model = (Config.GROQ_MODEL or "").strip()
    return MODEL_ALIASES.get(model, model or "llama-3.1-8b-instant")


def _auth_headers() -> Dict[str, str]:
    """Build headers for Groq's OpenAI-compatible REST API."""
    if not Config.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Get a free key at https://console.groq.com and add it to .env"
        )

    return {
        "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


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
    # Prepend the system prompt to give the model its persona
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers=_auth_headers(),
            json={
                "model": _configured_model(),
                "messages": messages,
                "max_tokens": 1024,        # Max length of the response
                "temperature": 0.7,        # 0=deterministic, 1=creative
                "top_p": 0.9,
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

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
        if (
            "model_not_found" in error_msg.lower()
            or "decommissioned" in error_msg.lower()
            or "not found" in error_msg.lower()
        ):
            raise RuntimeError(
                f"Groq model '{Config.GROQ_MODEL}' is unavailable. "
                "Set GROQ_MODEL=llama-3.1-8b-instant in your .env file."
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
        return {"status": "ok", "model": _configured_model(), "test_response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}
