import os
import numpy as np
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any
import re
import nltk
from nltk.tokenize import word_tokenize

# Download NLTK tokenizer data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# ---------- Embedding model (Bi‑Encoder) ----------
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# ---------- Cross‑Encoder (Re‑ranker) ----------
cross_encoder = None
try:
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    print("✅ Cross‑encoder loaded successfully.")
except Exception as e:
    print(f"⚠️ Cross‑encoder failed to load: {e}. Re‑ranking disabled.")

# ---------- ChromaDB ----------
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "clinic_docs"

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

# ---------- In‑memory store for BM25 ----------
_all_chunks = []          # list of dicts: {'text': str, 'metadata': dict}
_bm25_index = None        # BM25Okapi object, rebuilt after each index operation

def rebuild_bm25():
    """Rebuild the BM25 index from _all_chunks."""
    global _bm25_index
    if not _all_chunks:
        _bm25_index = None
        return
    tokenized_corpus = [word_tokenize(chunk['text'].lower()) for chunk in _all_chunks]
    _bm25_index = BM25Okapi(tokenized_corpus)

def load_all_chunks():
    """Load all existing documents from ChromaDB into _all_chunks."""
    global _all_chunks
    if _all_chunks:
        return
    try:
        all_data = collection.get(include=['documents', 'metadatas'])
        if all_data and all_data['documents']:
            for i, doc in enumerate(all_data['documents']):
                _all_chunks.append({
                    'text': doc,
                    'metadata': all_data['metadatas'][i] if all_data['metadatas'] else {}
                })
            rebuild_bm25()
            print(f"✅ Loaded {len(_all_chunks)} existing chunks from ChromaDB for BM25.")
        else:
            print("ℹ️ No existing documents found in ChromaDB.")
    except Exception as e:
        print(f"⚠️ Could not load existing chunks: {e}")

# Load chunks on module startup
load_all_chunks()

def get_embedding(text: str) -> np.ndarray:
    return embedding_model.encode(text)

def add_document_chunks(chunks: List[Dict[str, Any]]) -> None:
    global _all_chunks
    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for idx, chunk in enumerate(chunks):
        doc_id = f"{chunk['metadata'].get('source', 'unknown')}_{idx}"
        ids.append(doc_id)
        documents.append(chunk['text'])
        metadatas.append(chunk['metadata'])
        embeddings.append(get_embedding(chunk['text']))
        _all_chunks.append({
            'text': chunk['text'],
            'metadata': chunk['metadata']
        })

    if ids:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        rebuild_bm25()

def query_documents(query: str, top_k: int = 3, hybrid_alpha: float = 0.5, use_cross_encoder: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve top_k relevant document chunks for a query.
    If anything fails, fall back to pure semantic search.
    """
    # Ensure chunks are loaded (safety)
    if not _all_chunks:
        load_all_chunks()

    # Fallback function: pure semantic search
    def semantic_fallback(q, k):
        q_emb = get_embedding(q)
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=['documents', 'metadatas', 'distances']
        )
        if not res['documents'] or not res['documents'][0]:
            return []
        return [{
            'text': res['documents'][0][i],
            'metadata': res['metadatas'][0][i] if res['metadatas'] else {},
            'distance': res['distances'][0][i] if res['distances'] else 1.0
        } for i in range(len(res['documents'][0]))]

    # If no chunks in memory, fallback
    if not _all_chunks:
        return semantic_fallback(query, top_k)

    try:
        # 1. Semantic search
        semantic_top_k = 10 if use_cross_encoder else top_k
        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=semantic_top_k,
            include=['documents', 'metadatas', 'distances']
        )

        if not results['documents'] or not results['documents'][0]:
            return []

        candidates = []
        for i in range(len(results['documents'][0])):
            candidates.append({
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'semantic_score': 1 - results['distances'][0][i]
            })

        # 2. BM25 scores
        bm25_scores = [0] * len(_all_chunks)
        if _bm25_index is not None:
            query_tokens = word_tokenize(query.lower())
            raw_scores = _bm25_index.get_scores(query_tokens)
            max_score = max(raw_scores) if raw_scores else 1
            if max_score > 0:
                bm25_scores = [s / max_score for s in raw_scores]

        # 3. Combine scores
        for candidate in candidates:
            try:
                idx = next(i for i, ch in enumerate(_all_chunks) if ch['text'] == candidate['text'])
            except StopIteration:
                idx = -1
            bm25_score = bm25_scores[idx] if idx >= 0 and _bm25_index is not None else 0.0
            candidate['bm25_score'] = bm25_score
            candidate['hybrid_score'] = hybrid_alpha * candidate['semantic_score'] + (1 - hybrid_alpha) * bm25_score

        candidates.sort(key=lambda x: x['hybrid_score'], reverse=True)

        # 4. Cross-encoder re‑ranking
        if use_cross_encoder and cross_encoder is not None:
            rerank_candidates = candidates[:10]
            pairs = [(query, doc['text']) for doc in rerank_candidates]
            scores = cross_encoder.predict(pairs)
            for i, doc in enumerate(rerank_candidates):
                doc['cross_encoder_score'] = float(scores[i])
            rerank_candidates.sort(key=lambda x: x['cross_encoder_score'], reverse=True)
            final = rerank_candidates[:top_k]
        else:
            final = candidates[:top_k]

        return [{
            'text': doc['text'],
            'metadata': doc['metadata'],
            'distance': 1 - doc.get('hybrid_score', 0.5)
        } for doc in final]

    except Exception as e:
        # Fallback to semantic search
        print(f"⚠️ Advanced RAG error: {e}. Falling back to pure semantic search.")
        return semantic_fallback(query, top_k)

def clear_collection():
    global _all_chunks, _bm25_index
    chroma_client.delete_collection(COLLECTION_NAME)
    global collection
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    _all_chunks = []
    _bm25_index = None