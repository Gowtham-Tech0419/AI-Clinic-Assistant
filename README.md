# 🏥 AI Clinic Assistant

A production‑ready **AI‑powered clinic assistant** that combines a relational database, Retrieval‑Augmented Generation (RAG), and an intelligent LangGraph agent to help patients book, cancel, and reschedule appointments, as well as answer questions about clinic policies, insurance, and doctor profiles.

## ✨ Features

- **🤖 Intelligent Agent** – Built with LangGraph, the agent can reason, plan, and execute multi‑step tasks (e.g., check availability, book a slot, suggest alternatives).
- **📋 Appointment Management** – Full CRUD for appointments: book, cancel, reschedule with validation and transaction safety.
- **🧠 Memory & Multi‑turn Conversations** – Each user session has isolated memory, so the agent remembers context (e.g., “Book the 11:00 slot” after showing slots).
- **📄 RAG (Retrieval‑Augmented Generation)** – Index clinic policies, insurance PDFs, and doctor profiles; answer questions with grounded, up‑to‑date information.
- **🔍 Hybrid Search + Re‑ranking** – Combines BM25 keyword search with semantic search and cross‑encoder re‑ranking for highly accurate retrieval.
- **📎 PDF & Text Loading** – Upload `.txt` and `.pdf` documents; automatic chunking and embedding into ChromaDB.
- **💬 Web Chat Interface** – Modern, responsive HTML/CSS/JS chat UI with live messaging and session‑based isolation.
- **🔐 Secure** – API keys managed via environment variables; no hard‑coded secrets.

---

## 🛠️ Tech Stack

| Layer              | Technology |
|--------------------|------------|
| **Backend**        | Python 3.12, FastAPI, SQLAlchemy |
| **Database**       | SQLite (dev) / PostgreSQL (prod ready) |
| **LLM**            | Google Gemini 2.0 Flash (via LangChain) |
| **Embeddings**     | Sentence‑Transformers (`all‑MiniLM‑L6‑v2`) |
| **Vector DB**      | ChromaDB (persistent) |
| **RAG**            | Hybrid search (BM25 + semantic) + Cross‑encoder re‑ranking |
| **Agent Framework**| LangGraph with `MemorySaver` checkpointer |
| **PDF Parsing**    | PyMuPDF (fitz) |
| **Frontend**       | Vanilla HTML, CSS, JavaScript (no framework required) |
| **Deployment**     | Uvicorn, Docker‑ready |

---

## 📁 Project Structure


ai_clinical_assistant/
├── app/
│ ├── init.py
│ ├── agent.py # LangGraph agent with memory
│ ├── availability.py # Slot availability queries
│ ├── booking.py # Core booking logic
│ ├── database.py # SQLAlchemy setup
│ ├── embeddings.py # ChromaDB & embedding operations
│ ├── index_docs.py # Document indexing script
│ ├── llm.py # Gemini LLM instance
│ ├── main.py # FastAPI app & endpoints
│ ├── models.py # SQLAlchemy ORM models
│ ├── schemas.py # Pydantic schemas
│ ├── seed.py # Database seeding
│ ├── tools.py # LangChain tool definitions
│ └── static/ # Frontend assets
│ ├── index.html
│ ├── style.css
│ └── script.js
├── data/ # Place .txt and .pdf files here
├── chroma_db/ # Vector DB (auto‑created)
├── clinic.db # SQLite DB (auto‑created)
├── requirements.txt
├── .env # GEMINI_API_KEY
├── create_insurance_pdf.py # Helper to generate sample PDF
├── test_booking.py # Unit test for booking
├── view_db.py # Inspect database contents
├── test_retrieval.py # Test RAG retrieval
└── README.md


---

Architecture Overview

User (Web UI)  <-->  FastAPI Backend
                        |
                  +-----+------+
                  |            |
               SQL DB      Vector DB
               (CRUD)      (ChromaDB)
                  |            |
                  +-----+------+
                        |
                  LangGraph Agent
                  (with Tools + Memory)
                        |
                   Gemini LLM
