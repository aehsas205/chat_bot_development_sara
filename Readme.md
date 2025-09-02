# Aehsaas Foundation Chatbot - Documentation

## Project Overview
This is a FastAPI-based chatbot application for the Aehsaas Foundation, a nonprofit humanitarian organization. The chatbot uses RAG (Retrieval-Augmented Generation) to provide accurate information about the foundation's services, programs, and activities.

## Project Structure

### Core Files:
- `main.py` - FastAPI server with chat endpoint
- `config.py` - System configuration and session management
- `chatbot.py` - LangChain chatbot setup with Google Gemini model
- `graph.py` - LangGraph workflow definition
- `embed.py` - Document embedding and storage functionality
- `retriever.py` - Document retrieval tool
- `vectorstore_manager.py` - Chroma vector database management
- `feedback.py` - User feedback handling tool
- `samp.html` - Simple web interface for testing

### Directories:
- `chroma_index/` - Persistent vector database storage
- `all-MiniLM-L6-v2/` - Sentence transformer embedding model
- `venv/` - Python virtual environment

## Prerequisites

### 1. Python Environment
- Python 3.11 or higher
- Virtual environment (recommended)

### 2. Required Environment Variables
Create a `.env` file in the project root with:
```
GOOGLE_API_KEY=your_google_generative_ai_api_key
```

### 3. Dependencies
All dependencies are listed in `requirements.txt`

## Installation & Setup

### Step 1: Clone and Navigate
```bash
cd /path/to/aehsas_chatbot
```

### Step 2: Activate Virtual Environment
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables
Create a `.env` file with your Google API key:
```
GOOGLE_API_KEY=your_actual_api_key_here
```

## How to Run the Application

### Method 1: Run FastAPI Server
```bash
uvicorn main:app --reload
```
The server will start at `http://localhost:8000`

### Method 2: Run Simple Web Interface
```bash
python -m http.server 3000
```
Then open `http://localhost:3000/samp.html` in your browser

## API Endpoints

### Chat
- `POST /chat` - Send messages to the chatbot
  - Requires: `{"user_input": "your message"}`
  - Returns: `{"response": "bot response", "session_id": "session_id"}`

## Code Architecture Understanding

### 1. Main Application (`main.py`)
- **FastAPI Setup**: Creates the main application with CORS middleware
- **Session Management**: Automatic session cleanup for inactive users (60 minutes)
- **Endpoints**: Chat endpoint with session-based conversation memory
- **Lifespan Management**: Warm-up RAG pipeline on startup

### 2. Configuration (`config.py`)
- **System Message**: Defines the chatbot's behavior and scope
- **Memory Management**: Session-based conversation memory using LangGraph checkpointer
- **Session ID**: Unique identifier for each user session

### 3. Chatbot Engine (`chatbot.py`)
- **LLM Setup**: Google Gemini 2.0 Flash model
- **Tools Integration**: Binds retrieval and feedback tools
- **State Management**: Handles conversation state

### 4. Workflow Graph (`graph.py`)
- **LangGraph Setup**: Defines the conversation workflow
- **Tool Integration**: Connects chatbot with retrieval tools
- **Memory Checkpointing**: Persists conversation state

### 5. Document Processing (`embed.py`)
- **PDF Loading**: Uses PyMuPDF for PDF processing
- **Text Splitting**: Recursive character splitting for optimal chunks
- **Vector Storage**: Stores embeddings in Chroma database

### 6. Retrieval System (`retriever.py`)
- **Similarity Search**: Finds relevant documents based on user queries
- **Content Processing**: Cleans and formats retrieved content

### 7. Vector Database (`vectorstore_manager.py`)
- **Chroma Setup**: Persistent vector database configuration
- **Embedding Model**: HuggingFace sentence transformer
- **Collection Management**: Handles document collections

## Key Features

### 1. RAG (Retrieval-Augmented Generation)
- Documents are embedded and stored in a vector database
- Queries are matched against stored documents
- Responses are based on retrieved content, not hallucination

### 2. Multi-language Support
- Handles Hindi queries by translating to English for processing
- Returns responses in the original language

### 3. Session Management
- Maintains conversation context across multiple interactions
- Automatic cleanup of inactive sessions (60 minutes)

### 4. Feedback System
- Built-in feedback handling for user interactions
- Supports positive, negative, and human assistance requests

## Usage Examples

### 1. Starting the Server
```bash
# Terminal 1: Start FastAPI server
uvicorn main:app --reload

# Terminal 2: Start web interface (optional)
python -m http.server 3000
```

### 2. Testing the Chatbot
1. Open `http://localhost:3000/samp.html`
2. Type your question about Aehsaas Foundation
3. Click "Send" to get a response

### 3. Using the API Directly
```bash
# Send a chat message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What services does Aehsaas Foundation provide?"}'
```

## Troubleshooting

### Common Issues:

1. **Import Errors**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **API Key Issues**: Ensure your Google API key is set in `.env`
   ```
   GOOGLE_API_KEY=your_actual_key
   ```

3. **Port Conflicts**: Change ports if 8000 or 3000 are in use
   ```bash
   uvicorn main:app --reload --port 8001
   ```

4. **Memory Issues**: The application uses significant memory for embeddings
   - Ensure sufficient RAM (4GB+ recommended)
   - Monitor memory usage during document processing

### Debug Mode:
Enable debug logging by modifying the logging level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Session Management**: Sessions expire after 60 minutes of inactivity
3. **CORS**: Configured to allow localhost:3000 for web interface

## Performance Optimization

1. **Document Chunking**: Optimize chunk size in `embed.py` for your use case
2. **Vector Search**: Adjust `k` parameter in `retriever.py` for search results
3. **Memory Management**: Monitor session cleanup frequency
4. **Caching**: Consider implementing response caching for common queries

## Development Notes

- The system uses LangGraph for workflow management
- ChromaDB provides persistent vector storage
- Google Gemini 2.0 Flash powers the language model
- FastAPI provides the REST API framework
- Session-based memory maintains conversation context
- Automatic RAG pipeline warm-up on server startup

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code comments for implementation details
3. Monitor the console output for error messages
4. Ensure all dependencies are correctly installed
