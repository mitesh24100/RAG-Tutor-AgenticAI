import os
from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings


load_dotenv()

# You can pass model name; using nomic-embed-text as requested.
def get_embeddings(model_name: str = "nomic-embed-text"):
    # if using remote Nomic cloud you may need an API key available in env NOMIC_API_KEY
    return OllamaEmbeddings(model=model_name)