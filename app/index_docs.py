import os
import fitz  # PyMuPDF
from app.embeddings import add_document_chunks, clear_collection

def read_text_files(data_dir: str) -> list:
    """Read .txt files; returns list of (filename, content)."""
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append((filename, content))
    return documents

def extract_pdf_pages(filepath: str) -> list:
    """Extract text per page from PDF; returns list of (page_num, text)."""
    doc = fitz.open(filepath)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            pages.append((page_num, text))
    doc.close()
    return pages

def read_pdf_files(data_dir: str) -> list:
    """Read .pdf files; returns list of (filename, pages_list) where pages_list is list of (page_num, text)."""
    pdf_docs = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".pdf"):
            filepath = os.path.join(data_dir, filename)
            pages = extract_pdf_pages(filepath)
            if pages:
                pdf_docs.append((filename, pages))
    return pdf_docs

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
    """Main indexing function for .txt and .pdf files."""
    clear_collection()
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created {data_dir}. Please add .txt or .pdf files there.")
        return

    all_chunks = []

    # Process .txt files
    txt_files = read_text_files(data_dir)
    for filename, content in txt_files:
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                'text': chunk,
                'metadata': {
                    'source': filename,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'type': 'txt'
                }
            })

    # Process .pdf files
    pdf_files = read_pdf_files(data_dir)
    for filename, pages in pdf_files:
        for page_num, page_text in pages:
            chunks = chunk_text(page_text)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    'text': chunk,
                    'metadata': {
                        'source': filename,
                        'page': page_num,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'type': 'pdf'
                    }
                })

    if all_chunks:
        add_document_chunks(all_chunks)
        print(f"✅ Indexed {len(all_chunks)} chunks from {len(txt_files)} .txt and {len(pdf_files)} .pdf files.")
    else:
        print("No chunks to index.")

if __name__ == "__main__":
    index_all_documents()