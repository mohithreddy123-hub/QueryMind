import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google import genai
import chromadb

from config.settings import (
    GEMINI_API_KEY,
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    TOP_K,
)


def _get_gemini_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file: GEMINI_API_KEY=your_key"
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def _get_chroma_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        raise RuntimeError(
            f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' not found. "
            f"Run setup first: python setup/setup_chromadb.py"
        )

    if collection.count() == 0:
        raise RuntimeError(
            f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' exists but is empty. "
            f"Re-run: python setup/setup_chromadb.py --reset"
        )

    return collection


def embed_text(text: str) -> list[float]:
    client = _get_gemini_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
    )
    return result.embeddings[0].values


def retrieve_schema(question: str, top_k: int = TOP_K) -> list[dict]:
    question_embedding = embed_text(question)

    collection = _get_chroma_collection()

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids       = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved = []
    for table_id, doc_text, metadata, distance in zip(ids, documents, metadatas, distances):
        similarity = 1.0 - distance

        retrieved.append({
            "table_name":  table_id,
            "schema_text": doc_text,
            "description": metadata.get("description", ""),
            "similarity":  round(similarity, 4),
        })

    return retrieved


def format_schema_for_prompt(retrieved_docs: list[dict]) -> str:
    if not retrieved_docs:
        return "No relevant schema found."

    sections = []
    for doc in retrieved_docs:
        section = f"--- Schema: {doc['table_name']} ---\n{doc['schema_text']}"
        sections.append(section)

    return "\n\n".join(sections)
