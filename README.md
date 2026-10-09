# AI Clinic Assistant

An AI-powered virtual clinic assistant that helps patients interact with a clinic through a conversational interface. It allows patients to ask questions, find doctors, manage appointments, and retrieve clinic-related information using natural language.

The application combines Generative AI, Retrieval-Augmented Generation (RAG), and tool calling to provide helpful responses and perform appointment-related actions.

## Project Overview

Patients often need to contact a clinic to check doctor availability, book appointments, reschedule visits, or obtain information about clinic services. The AI Clinic Assistant simplifies these tasks through a conversational interface.

Users can interact with the assistant just as they would with a receptionist. The AI understands their requests, retrieves relevant information from the clinic's knowledge base, and uses connected tools to perform supported actions.

## Key Features

* **Conversational AI:** Understands patient questions and responds in natural language.
* **Appointment Booking:** Helps patients book appointments with available doctors.
* **Appointment Management:** Supports viewing, cancelling, and rescheduling appointments.
* **Doctor Availability:** Retrieves doctor information and availability.
* **Clinic Information:** Answers questions using relevant information from clinic documents.
* **Retrieval-Augmented Generation (RAG):** Retrieves relevant content from a knowledge base before generating answers.
* **Hybrid Search:** Combines semantic search and BM25 keyword search to find relevant information.
* **Cross-Encoder Reranking:** Reorders retrieved results to prioritize the most relevant content.
* **AI Tool Calling:** Allows the AI agent to invoke specific functions for appointment-related tasks.
* **Conversation Memory:** Maintains conversational context to support multi-turn interactions.
* **Document Processing:** Extracts text from PDF and TXT documents for the knowledge base.
* **REST API:** Uses FastAPI to provide backend endpoints for application functionality.

## Technology Stack

| Technology            | Purpose                                    |
| --------------------- | ------------------------------------------ |
| Python                | Core application development               |
| FastAPI               | Backend API development                    |
| Gemini API            | Large language model for conversational AI |
| LangChain             | LLM integration and tool orchestration     |
| LangGraph             | AI agent workflows and conversation state  |
| ChromaDB              | Vector storage for document embeddings     |
| Sentence Transformers | Text embeddings for semantic search        |
| BM25                  | Keyword-based document retrieval           |
| Cross-Encoder         | Reranking retrieved documents              |
| PyMuPDF               | Extracting text from PDF documents         |
| SQLAlchemy            | Database operations and ORM                |
| SQLite                | Storing appointment and application data   |
| HTML, CSS, JavaScript | Web-based chat interface                   |

## How It Works

The application follows a simple workflow:

1. The patient enters a question or request through the chat interface.
2. The backend sends the request to the AI agent.
3. The agent identifies the user's intent and determines whether it needs clinic information or an action.
4. For knowledge-based questions, the RAG pipeline retrieves relevant information using semantic and keyword search.
5. A cross-encoder reranks the retrieved results to improve relevance.
6. The language model generates a response using the available context.
7. For appointment-related requests, the agent calls the appropriate tool, such as booking, cancellation, rescheduling, or checking availability.
8. The backend processes the operation and returns the result to the user.

## System Architecture

```text
Patient
   |
   v
Chat Interface
   |
   v
FastAPI Backend
   |
   v
LangGraph AI Agent
   |
   +--------------------------+
   |                          |
   v                          v
Knowledge Retrieval       Appointment Tools
   |                          |
   v                          v
Semantic Search           SQLAlchemy
   |                      and Database
   v
BM25 Keyword Search
   |
   v
Cross-Encoder Reranking
   |
   v
Relevant Context
   |
   v
Gemini LLM
   |
   v
Response to Patient
```

## Retrieval-Augmented Generation (RAG)

RAG enables the assistant to answer questions using information from a clinic's own documents instead of relying only on the language model's existing knowledge.

The retrieval pipeline works as follows:

1. **Document ingestion:** Reads supported PDF and TXT files.
2. **Text extraction:** Extracts readable text using PyMuPDF where applicable.
3. **Chunking:** Splits documents into smaller sections for efficient retrieval.
4. **Embedding generation:** Converts text chunks into numerical representations using Sentence Transformers.
5. **Vector storage:** Stores embeddings in ChromaDB.
6. **Hybrid retrieval:** Uses semantic similarity and BM25 keyword matching to find relevant passages.
7. **Reranking:** Uses a cross-encoder to improve the ordering of retrieved passages.
8. **Answer generation:** Provides the retrieved context to the Gemini model to generate a relevant response.

This approach helps the assistant provide answers grounded in the available clinic documentation.

## Appointment Management

The AI agent can use dedicated tools to handle supported appointment operations.

| Tool                     | Function                                         |
| ------------------------ | ------------------------------------------------ |
| `show_doctors`           | Retrieves doctor information and availability    |
| `book_appointment`       | Books an appointment                             |
| `cancel_appointment`     | Cancels an existing appointment                  |
| `reschedule_appointment` | Changes an existing appointment                  |
| Appointment lookup       | Retrieves appointment details, where implemented |

The AI agent selects the appropriate tool based on the patient's request. The backend performs the actual operation through the application's database layer.

## Project Structure

The following is an example of how the project can be organized. Adjust the paths to match the actual files in your repository.

```text
AI-Clinic-Assistant/
|
|-- app/
|   |-- main.py
|   |-- agents/
|   |-- tools/
|   |-- routes/
|   |-- database/
|   |-- services/
|   |-- rag/
|
|-- documents/
|   |-- clinic_information.txt
|   |-- clinic_information.pdf
|
|-- static/
|   |-- style.css
|   |-- script.js
|
|-- templates/
|   |-- index.html
|
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
```

## Installation and Setup

### Prerequisites

Make sure the following are installed:

* Python 3.10 or a compatible version supported by your dependencies
* Git
* A Gemini API key
* A terminal or command prompt

### 1. Clone the Repository

```bash
git clone https://github.com/Gowtham-Tech0419/AI-Clinic-Assistant.git
cd AI-Clinic-Assistant
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and add the required configuration.

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///./clinic.db
```

Use the exact environment variable names expected by your application. The database URL shown above is an example; adjust it if your project uses a different configuration.

Never commit your actual API key or other secrets to GitHub.

### 5. Run the Application

If your FastAPI entry point is `app/main.py`, run:

```bash
uvicorn app.main:app --reload
```

If your entry point is located elsewhere, replace `app.main:app` with the appropriate Python module and application object.

Open the local address displayed in the terminal. FastAPI's interactive API documentation is generally available at:

```text
http://127.0.0.1:8000/docs
```

The chat interface URL depends on how the frontend is configured in your application.

## Example Interactions

**Checking doctor availability**

Patient: Which doctors are available?

Assistant: I can check the available doctors and provide their details.

**Booking an appointment**

Patient: I want to book an appointment with a doctor.

Assistant: I can help you find an available doctor and proceed with booking. Please provide the required appointment details.

**Asking a clinic-related question**

Patient: What are the clinic's working hours?

Assistant: The assistant retrieves the relevant information from the clinic knowledge base and responds based on the available documents.

These examples illustrate intended interactions. Actual responses depend on the configured knowledge base, available doctors, and application implementation.

## Database Design

The application uses SQLAlchemy to interact with the database.

The database layer supports structured storage and management of appointment information. SQLite provides a lightweight database option for local development, while the application can be configured for a different database if the required setup is implemented.

## Future Enhancements

* Voice input for hands-free patient interaction.
* Voice responses for a more natural conversational experience.
* Improved appointment reminders and notifications.
* Authentication and role-based access for patients and clinic staff.
* Enhanced monitoring, logging, and error handling.
* Cloud deployment and automated CI/CD.
* Expanded multilingual support.

## Security and Responsible Use

* Keep API keys and credentials in environment variables.
* Validate user input before performing database operations.
* Protect patient and appointment information with appropriate access controls.
* Avoid exposing sensitive information in application logs or error messages.
* Verify appointment details before confirming changes.
* Treat AI-generated information as assistance, not as a substitute for professional medical advice.

## Learning Outcomes

This project demonstrates practical experience with:

* Integrating large language models into an application.
* Building AI agents with tool calling and workflow orchestration.
* Implementing a RAG pipeline for document-based question answering.
* Combining semantic search with keyword-based retrieval.
* Improving retrieval quality with cross-encoder reranking.
* Developing REST APIs using FastAPI.
* Connecting AI workflows to a relational database.
* Maintaining conversational context across multiple interactions.

## Author

**Gowtham G**

Generative AI Engineer | Python Developer | LLM and RAG

* GitHub: https://github.com/Gowtham-Tech0419
* LinkedIn: https://www.linkedin.com/in/here-gowtham-g/
* Portfolio: https://gowthamgopalakrishnan.vercel.app/

---

If you find this project interesting, feel free to explore the repository and share suggestions for improvement.
