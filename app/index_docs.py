import os
from app.embeddings import add_document_chunks, clear_collection

def read_text_files(data_dir: str) -> list:
    """Read all .txt files from data_dir and return a list of (filename, content)."""
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append((filename, content))
    return documents

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap
    return chunks

def index_all_documents():
    """Main indexing function."""
    # Clear existing collection to avoid duplicates
    clear_collection()
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created {data_dir}. Please add .txt files there.")
        return

    files = read_text_files(data_dir)
    if not files:
        print(f"No .txt files found in {data_dir}.")
        return

    all_chunks = []
    for filename, content in files:
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                'text': chunk,
                'metadata': {
                    'source': filename,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            })

    if all_chunks:
        add_document_chunks(all_chunks)
        print(f"✅ Indexed {len(all_chunks)} chunks from {len(files)} files.")
    else:
        print("No chunks to index.")

if __name__ == "__main__":
    index_all_documents()