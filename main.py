"""
AEHSAS Foundation AI Assistant - FastAPI Backend Server
======================================================
"""

"""import os
import time
import asyncio
import shutil
import traceback
from fastapi import FastAPI, Request, Response, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

# Load environment configuration
from dotenv import load_dotenv
load_dotenv()

from graph import graph
from feedback import store_unanswered_query, send_error_notification, send_email_alert

# 1. Added reindex_website_only import here
from scrape_and_embed import process_and_embed_pdf, reindex_website_only

app = FastAPI(title="AEHSAS Foundation Chatbot API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_input: str
    session_id: str = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "samp.html")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Admin authentication key from .env (fallback default provided for dev)
ADMIN_SECRET = os.getenv("ADMIN_SECRET_KEY", "aehsas_admin_123")


def get_or_create_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = f"session_{int(time.time() * 1000)}"
        response.set_cookie(key="session_id", value=session_id)
    return session_id


@app.get("/")
async def serve_frontend():
    if not os.path.exists(HTML_PATH):
        return JSONResponse(status_code=404, content={"detail": "samp.html file not found."})
    return FileResponse(HTML_PATH)


@app.post("/chat")
async def chat_endpoint(data: ChatRequest, request: Request, response: Response):
    cleaned_input = data.user_input.strip() if data.user_input else ""
    if not cleaned_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    session_id = data.session_id or request.headers.get("X-Session-ID") or get_or_create_session_id(request, response)
    if not session_id or session_id.strip() == "":
        session_id = f"session_{int(time.time() * 1000)}"

    print(f"\n================ [INCOMING REQUEST] ================")
    print(f"📩 Input: {cleaned_input}")
    print(f"🔑 Session ID: {session_id}")
    print(f"====================================================\n")

    try:
        
        config = {"configurable": {"thread_id": session_id}}
        user_message = HumanMessage(content=cleaned_input)

        
        response_obj = await asyncio.to_thread(
            graph.invoke,
            {"messages": [user_message]},
            config=config
        )

        if not response_obj or "messages" not in response_obj or not response_obj["messages"]:
            raise ValueError("Invalid or empty response returned from Graph pipeline.")

        last_message = response_obj["messages"][-1]
        
        if isinstance(last_message.content, str):
            reply = last_message.content
        elif isinstance(last_message.content, list):
            reply = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in last_message.content])
        else:
            reply = str(last_message.content)

        # --- Automatic Unanswered Query Detector & Logger ---
        fallback_keywords = [
            "don't know", "don't have information", "not sure", 
            "unable to find", "pata nahi", "sorry, i cannot",
            "does not contain", "cannot answer", "no information", "not available", "not provided", "provided database context", "not mention", "no mention"
        ]
        
        if any(keyword in reply.lower() for keyword in fallback_keywords):
            # 1. Save in local JSON file
            store_unanswered_query(user_query=cleaned_input, session_id=session_id)
            
            # 2. Trigger Email Alert to Admin
            try:
                subject = f"⚠️ Unanswered Query Alert: Session {session_id}"
                body = (
                    f"The chatbot encountered a query that is not in the knowledge base.\n\n"
                    f"📌 User Query: {cleaned_input}\n"
                    f"🔑 Session ID: {session_id}\n"
                    f"🤖 Bot Reply: {reply}\n"
                )
                send_email_alert(subject=subject, body=body)
            except Exception as mail_err:
                print(f"⚠️ Failed to dispatch unanswered query email alert: {mail_err}")

        print(f"✅ [SUCCESS RESPONSE]: {reply[:100]}...\n")
        return {"response": reply, "session_id": session_id}

    except Exception as e:
        tb_str = traceback.format_exc()
        print("\n================ ❌ CRITICAL BACKEND ERROR ❌ ================")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(tb_str)
        print("===============================================================\n")
        
        # 🚨 Automatic Error Email Notification Trigger
        try:
            send_error_notification(
                error_type=type(e).__name__,
                error_msg=str(e),
                traceback_details=tb_str
            )
        except Exception as mail_err:
            print(f"⚠️ Failed to dispatch error email alert: {mail_err}")
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Backend Error [{type(e).__name__}]: {str(e)}"}
        )


# =====================================================================
# 🛠️ ADMIN PANEL 1: PDF UPLOAD & RE-INDEXING ENDPOINT
# =====================================================================
@app.post("/admin/upload-pdf")
async def upload_pdf_and_reindex(
    file: UploadFile = File(...),
    admin_key: str = Form(...)
):
    # 1. Check Authentication Secret
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    # 2. Verify File Extension
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # 3. Save File to uploads/ folder
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"📄 Saved new PDF: {file.filename}")

        # 4. Trigger Vector Store Re-indexing
        num_chunks = await asyncio.to_thread(process_and_embed_pdf, file_path)

        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and successfully embedded {num_chunks} chunks into Knowledge Base!",
            "filename": file.filename,
            "chunks_added": num_chunks
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        try:
            
            send_error_notification(
                error_type="AdminReindexError",
                error_msg=str(e),
                traceback_details=tb_str
            )
        except Exception as mail_err:
            print(f"⚠️ Failed to dispatch admin upload error email: {mail_err}")

        raise HTTPException(status_code=500, detail=f"Failed to upload and re-index PDF: {str(e)}")


# =====================================================================
# 🌐 ADMIN PANEL 2: WEBSITE RE-SCRAPING & RE-INDEXING ENDPOINT
# =====================================================================
@app.post("/admin/reindex-website")
async def trigger_website_reindex(
    admin_key: str = Form(...)
):
    # 1. Check Authentication Secret
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    try:
        # 2. Trigger Website Re-scraping
        chunks_added = await asyncio.to_thread(reindex_website_only)

        return {
            "status": "success",
            "message": f"Website re-scraped and updated successfully! ({chunks_added} chunks embedded)",
            "chunks_added": chunks_added
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        try:
            send_error_notification(
                error_type="WebsiteReindexError",
                error_msg=str(e),
                traceback_details=tb_str
            )
        except Exception as mail_err:
            print(f"⚠️ Failed to dispatch website reindex error email: {mail_err}")

        raise HTTPException(status_code=500, detail=f"Failed to re-index website: {str(e)}")"""

"""
AEHSAS Foundation AI Assistant - FastAPI Application Entry Point
===============================================================
"""
"""
AEHSAS Foundation AI Assistant - FastAPI Application Entry Point
===============================================================
"""
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# ⚡ Smart Import: Auto-detects variable name from graph.py
try:
    from graph import app as agent_app
except ImportError:
    try:
        from graph import graph as agent_app
    except ImportError:
        from graph import workflow as agent_app

from vectorstore_manager import get_vectorstore, PERSIST_DIR

app = FastAPI(title="AEHSAS Foundation Chatbot API")

# Setup Templates & Static Files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class QueryRequest(BaseModel):
    message: str


@app.on_event("startup")
async def startup_event():
    """Ensure vectorstore is loaded without re-scraping or wiping database."""
    print("🚀 Server starting up...")
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print("✅ Pre-built ChromaDB index found! Loading existing vector store...")
        get_vectorstore()
    else:
        print("⚠️ ChromaDB index not found! Please build index locally and push.")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main Chatbot UI page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat")
async def chat_endpoint(payload: QueryRequest):
    """Handles user queries and returns responses from LangGraph agent."""
    try:
        user_message = payload.message.strip()
        if not user_message:
            return JSONResponse(status_code=400, content={"error": "Message cannot be empty."})

        # Run state through LangGraph pipeline
        inputs = {"messages": [("user", user_message)]}
        result = agent_app.invoke(inputs)
        
        # Extract last message from agent response
        last_msg = result["messages"][-1]
        response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        return {"response": response_text}

    except Exception as e:
        print(f"Error processing chat request: {e}")
        return JSONResponse(status_code=500, content={"error": "An error occurred while processing your request."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)