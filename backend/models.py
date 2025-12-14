import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama


load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")

def get_chat_model(temperature: float = 0.2, max_tokens: int | None = None):
    """
    Returns a ChatOllama model object to be used like a LangChain chat model.
    """
    # ChatOllama accepts model and base_url kwargs in many integrations
    kwargs = {"model": LLM_MODEL, "base_url": OLLAMA_BASE_URL, "temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOllama(**kwargs)