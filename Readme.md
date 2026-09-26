# AEHSAS Foundation Chatbot — Technical Documentation & Runbook

An asynchronous Retrieval-Augmented Generation (RAG) conversational engine designed for the AEHSAS Foundation. Built on FastAPI, LangGraph, ChromaDB, and Google Gemini 2.5 Flash, the service provides verified, hallucination-free answers regarding foundation programs, donation routes, membership fees, and contact details.

**Live Deployment URL**: https://chat-bot-development.onrender.com/
---

## 1. Project Architecture & Directory Structure

```text
chat_bot_development/
├── .github/
│   └── workflows/
│       ├── auto_sync.yml            # Automated scraping & index sync pipeline
│       ├── ci-cd.yml                # Build, test, and Render deployment workflow
│       └── trigger_chatbot.yml      # Cross-repo repository dispatch trigger
├── all-MiniLM-L6-v2/                # Local HuggingFace sentence transformer weights
├── chroma_index/                    # Persistent ChromaDB vector database storage
├── uploads/                         # Staging directory for Google Drive synced PDFs
├── .env.example                     # Environment variable template
├── .gitignore                       # Ignored paths (.env, caches, indexes)
├── chatbot.py                       # LangChain/Gemini LLM initialization & tool bindings
├── config.py                        # System prompts, grounded directives, and constants
├── Dockerfile                       # Container deployment definition
├── embed.py                         # PDF document loader (PyMuPDF) and recursive chunker
├── feedback.py                      # Observability, unanswered queries & escalation routing
├── google_credentials.json          # Google Drive API service credentials (git-ignored)
├── graph.py                         # LangGraph StateGraph, tool loops & MemorySaver checkpointer
├── main.py                          # FastAPI ASGI gateway, CORS, and chat endpoints
├── mcp_client.py                    # FastMCP tool integrations (donation & fee calculations)
├── mcp_server.py                    # Local Model Context Protocol server definition
├── processed_drive_files.json       # State tracker for synced Google Drive documents
├── requirements.txt                 # Project dependencies
├── retriever.py                     # Vector store retrieval tool & candidate expansion logic
├── samp.html                        # Frontend testing chat widget with voice & SSE typing
├── scrape_and_embed.py              # Headless Selenium website extraction & re-indexing
└── vectorstore_manager.py           # ChromaDB index lifecycle and embedding initialization

## 2. Prerequisites
Python Version: Python 3.10 is required[cite: 2].

Google Cloud / AI Studio: Valid API key enabled for Gemini 2.5 Flash

Google Drive API: Service account JSON credentials configured with read access to the designated folder

## 3. Environment Configuration
Create a .env file in the project root director
# LLM & Embedding Credentials
GOOGLE_API_KEY="your_google_generative_ai_api_key"

# Knowledge Ingestion & Sync
GOOGLE_DRIVE_FOLDER_ID="your_google_drive_folder_id"
CHATBOT_TRIGGER_TOKEN="your_github_personal_access_token"

# Automated Escalation & Notification
SENDER_EMAIL="notifications@gmail.com"
SENDER_PASSWORD="your_smtp_app_password"
ADMIN_EMAIL="admin_email_id@gmail.com"

4. Installation & Local Setup

Step 1: Clone Repository and Navigate Bash
git clone [https://github.com/your-org/chat_bot_development.git](https://github.com/your-org/chat_bot_development.git)
cd chat_bot_development

Step 2: Create and Activate Virtual Environment
# Linux / macOS
python3.10 -m venv venv
source venv/bin/activate

# Windows (Command Prompt / PowerShell)
python -m venv venv
venv\Scripts\activate

Step 3: Install Required Dependencies
pip install --upgrade pip
pip install -r requirements.txt

## 5. Knowledge Base Ingestion & Vector Indexing
Before launching the server for the first time, populate the vector store:
Ingest Local PDFs
python embed.py
Automated Website Scraping & Re-indexing
python -c "from scrape_and_embed import reindex_website_only; reindex_website_only()"

## 6. Running the Application
Start FastAPI Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
