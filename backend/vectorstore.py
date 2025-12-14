import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from embeddings import get_embeddings

load_dotenv()
INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "./data/faiss_index")

def create_or_load_faiss(embeddings=None, index_path: str = INDEX_DIR):
    """
    Create a new FAISS store or load existing from index_path.
    Returns: (faiss_store, embeddings)
    """
    if embeddings is None:
        embeddings = get_embeddings()

    # If index dir exists and contains saved index, load it
    if os.path.exists(index_path) and len(os.listdir(index_path)) > 0:
        try:
            faiss_store = FAISS.load_local(index_path, embeddings)
            return faiss_store, embeddings
        except Exception:
            # fallback: create empty
            pass

    # Create empty FAISS store (no docs)
    # create with a small dummy doc then remove later, or use from_documents when adding
    faiss_store = None
    return faiss_store, embeddings

def save_faiss(faiss_store: FAISS, index_path: str = INDEX_DIR):
    os.makedirs(index_path, exist_ok=True)
    faiss_store.save_local(index_path)

def add_texts(faiss_store: FAISS | None, texts: list[str], metadatas: list[dict] | None = None):
    """
    Add texts to FAISS. If faiss_store is None, create new store from texts.
    """
    embeddings = get_embeddings()
    docs = [Document(page_content=t, metadata=(m if m else {})) for t, m in zip(texts, metadatas or [{}]*len(texts))]
    if faiss_store is None:
        faiss_store = FAISS.from_documents(docs, embeddings)
    else:
        faiss_store.add_documents(docs)
    return faiss_store

def similarity_search(faiss_store: FAISS, query: str, k: int = 4):
    if faiss_store is None:
        return []
    return faiss_store.similarity_search(query, k=k)