from app.embeddings import collection

# Get all documents in ChromaDB
all_docs = collection.get(include=['metadatas', 'documents'])
print(f"Total chunks: {len(all_docs['ids'])}")

# Check if any have 'insurance' in metadata
for i, meta in enumerate(all_docs['metadatas']):
    if 'insurance' in meta.get('source', '').lower():
        print(f"Found insurance chunk: {meta['source']} - {all_docs['documents'][i][:100]}...")