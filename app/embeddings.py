import os
import numpy as np
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

# Initialize embedding model (returns numpy arrays by default)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# ChromaDB persistent client
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "clinic_docs"

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

def get_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a single text.
    Returns a numpy array of shape (embedding_dim,).
    """
    return embedding_model.encode(text)  # already numpy array

def add_document_chunks(chunks: List[Dict[str, Any]]) -> None:
    """
    Add document chunks to the vector DB.
    Each chunk: { 'text': str, 'metadata': {'source': str, 'chunk_index': int, ...} }
    """
    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for idx, chunk in enumerate(chunks):
        doc_id = f"{chunk['metadata'].get('source', 'unknown')}_{idx}"
        ids.append(doc_id)
        documents.append(chunk['text'])
        metadatas.append(chunk['metadata'])
        embeddings.append(get_embedding(chunk['text']))  # numpy array

    if ids:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings   # list of numpy arrays is accepted
        )

def query_documents(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top_k relevant document chunks for a query.
    Returns a list of dicts with 'text', 'metadata', and 'distance'.
    """
    query_embedding = get_embedding(query)  # numpy array
    results = collection.query(
        query_embeddings=[query_embedding],  # list of numpy arrays
        n_results=top_k,
        include=['documents', 'metadatas', 'distances']
    )

    retrieved = []
    if results['documents'] and results['documents'][0]:
        for i in range(len(results['documents'][0])):
            retrieved.append({
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'distance': results['distances'][0][i] if results['distances'] else 1.0
            })
    return retrieved

def clear_collection():
    """Delete all documents from the collection."""
    chroma_client.delete_collection(COLLECTION_NAME)
    global collection
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)