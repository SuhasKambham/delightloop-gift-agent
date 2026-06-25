from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


def _configure_tracing():
    """Enable LangSmith tracing when credentials are present."""
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", "delightloop-gift-agent")


_configure_tracing()


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
    )
