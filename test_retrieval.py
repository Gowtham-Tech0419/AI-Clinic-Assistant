from app.embeddings import query_documents

query = "What does the insurance policy cover?"
results = query_documents(query, top_k=3)

print(f"Query: {query}")
print(f"Found {len(results)} chunks:")
for i, r in enumerate(results):
    print(f"\n--- Chunk {i+1} ---")
    print(f"Source: {r['metadata'].get('source', 'unknown')}")
    print(f"Text: {r['text'][:200]}...")