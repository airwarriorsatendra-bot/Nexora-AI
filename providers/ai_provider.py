import os

provider = os.getenv("AI_PROVIDER", "groq").lower()

if provider == "groq":
    from providers.groq_provider import chat

elif provider == "gemini":
    from providers.gemini_provider import chat

elif provider == "openai":
    from providers.openai_provider import chat

else:
    raise ValueError(f"Unsupported AI provider: {provider}")

__all__ = ["chat"]