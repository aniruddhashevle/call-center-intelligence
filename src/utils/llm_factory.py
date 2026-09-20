from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


def get_llm(provider: str, model: str | None = None, timeout: float = 60):
    """
    Create an LLM client for the selected provider.

    Supported providers:
        openai
        gemini
        groq
    """

    provider = provider.lower().strip()

    if provider == "openai":
        return ChatOpenAI(
            model=model or "gpt-4o",
            timeout=timeout,
        )

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model or "gemini-3.6-flash",
            timeout=timeout,
        )

    if provider == "groq":
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            timeout=timeout,
        )

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )