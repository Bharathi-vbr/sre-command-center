"""
RAG Vector Store Wrapper

Manages ChromaDB persistence for runbooks and incidents.
Uses HuggingFace all-MiniLM-L6-v2 for embeddings.
"""

import os
from typing import Optional, List, Dict
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


def get_vector_store():
    """
    Initialize ChromaDB persistent vector store.
    
    Returns:
        chromadb.PersistentClient: ChromaDB client configured for local persistence
    """
    persist_dir = "./chroma_db"
    os.makedirs(persist_dir, exist_ok=True)
    
    client = chromadb.PersistentClient(path=persist_dir)
    return client


def get_or_create_collection(client, collection_name: str, embedding_function=None):
    """
    Get or create a ChromaDB collection.

    Args:
        client: ChromaDB client
        collection_name: Name of collection (e.g., "runbooks", "incidents")
        embedding_function: Embedding function; defaults to ONNX all-MiniLM-L6-v2

    Returns:
        chromadb.Collection: Collection reference
    """
    ef = embedding_function if embedding_function is not None else DefaultEmbeddingFunction()
    try:
        collection = client.get_collection(name=collection_name, embedding_function=ef)
    except Exception:
        collection = client.create_collection(
            name=collection_name,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return collection


def add_documents(
    collection,
    documents: List[str],
    metadatas: List[Dict],
    ids: Optional[List[str]] = None
) -> None:
    """
    Add documents to a collection.
    
    Args:
        collection: ChromaDB collection
        documents: List of document texts
        metadatas: List of metadata dicts (one per document)
        ids: Optional list of document IDs
    """
    if ids is None:
        ids = [f"doc_{i}" for i in range(len(documents))]
    
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )


def search_documents(
    collection,
    query: str,
    n_results: int = 5
) -> List[Dict]:
    """
    Search documents by semantic similarity.
    
    Args:
        collection: ChromaDB collection
        query: Search query text
        n_results: Number of results to return
        
    Returns:
        List of dicts with 'id', 'document', 'metadata', 'distance'
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    formatted_results = []
    if results["ids"] and len(results["ids"]) > 0:
        for i, doc_id in enumerate(results["ids"][0]):
            formatted_results.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0
            })
    
    return formatted_results


def clear_collection(client, collection_name: str) -> None:
    """
    Clear all documents from a collection.
    
    Args:
        client: ChromaDB client
        collection_name: Name of collection to clear
    """
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass


_vector_store = None


def get_store():
    """Get initialized vector store (lazy initialization). Returns the ChromaDB client."""
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store
