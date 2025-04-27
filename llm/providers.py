"""Multi-provider LLM support for Hisaab.

Supports:
- Google Gemini (via ``google-generativeai`` package)
- OpenAI-compatible APIs (via ``openai`` package — works with OpenAI, Groq, Together, etc.)

Providers are imported lazily so that missing packages only raise at call time,
not at import time. Install only the packages you need.

Usage::

    from llm.providers import generate

    text = generate(
        prompt="Summarise this data...",
        api_key="your-key-here",
        provider="gemini",
        model=None,   # uses default for the provider
    )
"""

from __future__ import annotations

from typing import Literal

# NOTE: Rate limiting is intentionally NOT implemented here.
# The FastAPI layer should apply per-IP rate limiting (e.g. slowapi) before
# requests reach this function. Each user supplies their own key, so
# quota enforcement is handled by the upstream LLM provider.

Provider = Literal["gemini", "openai", "groq", "together"]

# Default model per provider — users can override via the ``model`` argument.
PROVIDER_DEFAULTS: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "together": "meta-llama/Llama-3-70b-chat-hf",
}

# Base URLs for OpenAI-compatible providers.
_OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
}


def _generate_gemini(prompt: str, api_key: str, model: str) -> str:
    """Call Google Gemini. Requires ``google-generativeai>=0.8.0``."""
    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is not installed. "
            "Run: pip install 'google-generativeai>=0.8.0'"
        ) from exc

    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    response = client.generate_content(prompt)
    return response.text


def _generate_openai_compat(
    prompt: str,
    api_key: str,
    model: str,
    base_url: str | None,
) -> str:
    """Call any OpenAI-compatible API. Requires ``openai>=1.0.0``."""
    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "openai is not installed. Run: pip install 'openai>=1.0.0'"
        ) from exc

    kwargs: dict[str, object] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)  # type: ignore[arg-type]
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = completion.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned an empty response")
    return content


def generate(
    prompt: str,
    api_key: str,
    provider: Provider,
    model: str | None = None,
) -> str:
    """Generate text from an LLM given a prompt and user-supplied API key.

    Args:
        prompt:   The full prompt to send to the model.
        api_key:  The user's API key. Never stored or logged.
        provider: One of "gemini", "openai", "groq", "together".
        model:    Optional model name override. Falls back to PROVIDER_DEFAULTS.

    Returns:
        The model's text response as a plain string.

    Raises:
        ImportError: If the required package is not installed.
        ValueError:  If the provider is unrecognised or the response is empty.
    """
    resolved_model = model or PROVIDER_DEFAULTS.get(provider)
    if resolved_model is None:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Valid providers: {list(PROVIDER_DEFAULTS)}"
        )

    if provider == "gemini":
        return _generate_gemini(prompt, api_key, resolved_model)

    if provider in ("openai", "groq", "together"):
        base_url = _OPENAI_COMPAT_BASE_URLS.get(provider)
        return _generate_openai_compat(prompt, api_key, resolved_model, base_url)

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Valid providers: {list(PROVIDER_DEFAULTS)}"
    )
