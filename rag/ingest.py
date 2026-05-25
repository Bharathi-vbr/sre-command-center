"""
RAG Data Ingestion

Reads runbooks and incidents from markdown files,
chunks them, and stores in ChromaDB vector store.
"""

import os
import sys
import glob
from pathlib import Path
from typing import List, Tuple
from rag.store import get_vector_store, get_or_create_collection


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Full text to chunk
        chunk_size: Target characters per chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def load_markdown_files(directory: str) -> List[Tuple[str, str]]:
    """
    Load all markdown files from directory.
    
    Args:
        directory: Path to directory containing .md files
        
    Returns:
        List of tuples (filename, content)
    """
    files = []
    
    if not os.path.exists(directory):
        print(f"⚠️  Directory not found: {directory}")
        return files
    
    for md_file in glob.glob(os.path.join(directory, "*.md")):
        try:
            with open(md_file, "r") as f:
                content = f.read()
                filename = os.path.basename(md_file)
                files.append((filename, content))
        except Exception as e:
            print(f"❌ Error reading {md_file}: {e}")
    
    return files


def ingest_collection(
    collection_name: str,
    directory: str,
    store
) -> int:
    """
    Ingest all documents from a directory into a collection.
    
    Args:
        collection_name: Name of ChromaDB collection
        directory: Path to directory with markdown files
        embeddings: Embeddings model
        store: ChromaDB client
        
    Returns:
        Total number of chunks ingested
    """
    files = load_markdown_files(directory)
    
    if not files:
        print(f"  ⚠️  No files found in {directory}")
        sys.stdout.flush()
        return 0
    
    print(f"  • Found {len(files)} file(s)")
    sys.stdout.flush()
    print(f"  • Creating collection '{collection_name}'...")
    sys.stdout.flush()
    
    try:
        collection = get_or_create_collection(
            store,
            collection_name,
            embedding_function=None
        )
        print(f"  ✓ Collection created")
        sys.stdout.flush()
    except Exception as e:
        print(f"  ❌ Failed to create collection: {e}")
        sys.stdout.flush()
        return 0
    
    total_chunks = 0
    batch_size = 10
    
    for filename, content in files:
        # Chunk the content
        chunks = chunk_text(content, chunk_size=500, overlap=100)
        print(f"  • {filename}: {len(chunks)} chunks")
        sys.stdout.flush()
        
        # Batch add documents
        documents = []
        metadatas = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            doc_id = f"{filename.replace('.md', '')}_{idx}"
            metadata = {
                "source": filename,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            }
            
            documents.append(chunk)
            metadatas.append(metadata)
            ids.append(doc_id)
        
        # Add batch to collection
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            total_chunks += len(documents)
            print(f"    ✓ Added {len(documents)} chunks")
            sys.stdout.flush()
        except Exception as e:
            print(f"    ❌ Error: {e}")
            sys.stdout.flush()
    
    return total_chunks


def ingest_all():
    """
    Main ingestion pipeline.
    Ingest runbooks and incidents into vector store.
    """
    print("🚀 Starting RAG ingestion...")
    sys.stdout.flush()
    
    store = get_vector_store()
    print("✓ Vector store initialized")
    sys.stdout.flush()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    runbooks_dir = os.path.join(base_dir, "data", "runbooks")
    print(f"📚 Ingesting runbooks...")
    sys.stdout.flush()
    runbook_chunks = ingest_collection("runbooks", runbooks_dir, store)
    print(f"Ingested {runbook_chunks} runbook chunks")
    sys.stdout.flush()

    incidents_dir = os.path.join(base_dir, "data", "incidents")
    print(f"📋 Ingesting incidents...")
    sys.stdout.flush()
    incident_chunks = ingest_collection("incidents", incidents_dir, store)
    print(f"Ingested {incident_chunks} incident chunks")
    sys.stdout.flush()


if __name__ == "__main__":
    ingest_all()
