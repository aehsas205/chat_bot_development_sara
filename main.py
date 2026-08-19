"""
AEHSAS Foundation AI Assistant - FastAPI Streaming Backend Server
================================================================
"""

"""import os
import time
import asyncio
import shutil
import traceback
from fastapi import FastAPI, Request, Response, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# Load environment configuration
from dotenv import load_dotenv
load_dotenv()

from chatbot import stream_chat_response
from feedback import store_unanswered_query, send_error_notification, send_email_alert
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

    print(f"\n================ [STREAMING REQUEST] ================")
    print(f"📩 Input: {cleaned_input}")
    print(f"🔑 Session ID: {session_id}")
    print(f"====================================================\n")

    async def token_streamer():
        full_reply = ""
        try:
            # Yields words/tokens as they stream in real-time from Gemini
            for token in stream_chat_response(cleaned_input):
                full_reply += token
                yield token
                await asyncio.sleep(0.005)

            # --- Automatic Unanswered Query Detector & Logger ---
            fallback_keywords = [
                "don't know", "don't have information", "not sure", 
                "unable to find", "pata nahi", "sorry, i cannot",
                "does not contain", "cannot answer", "no information", 
                "not available", "not provided", "provided database context", 
                "not mention", "no mention"
            ]
            
            if any(keyword in full_reply.lower() for keyword in fallback_keywords):
                store_unanswered_query(user_query=cleaned_input, session_id=session_id)
                try:
                    subject = f"⚠️ Unanswered Query Alert: Session {session_id}"
                    body = (
                        f"The chatbot encountered a query that is not in the knowledge base.\n\n"
                        f"📌 User Query: {cleaned_input}\n"
                        f"🔑 Session ID: {session_id}\n"
                        f"🤖 Bot Reply: {full_reply}\n"
                    )
                    send_email_alert(subject=subject, body=body)
                except Exception as mail_err:
                    print(f"⚠️ Failed to dispatch unanswered query email alert: {mail_err}")

        except Exception as e:
            tb_str = traceback.format_exc()
            print("\n================ ❌ STREAMING ERROR ❌ ================")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(tb_str)
            print("=======================================================\n")
            
            try:
                send_error_notification(
                    error_type=type(e).__name__,
                    error_msg=str(e),
                    traceback_details=tb_str
                )
            except Exception as mail_err:
                print(f"⚠️ Failed to dispatch error email alert: {mail_err}")
                
            yield "\n[Error: An internal issue occurred while generating the response.]"

    return StreamingResponse(
        token_streamer(),
        media_type="text/plain",
        headers={
            "X-Session-ID": session_id,
            "Cache-Control": "no-cache"
        }
    )


# =====================================================================
# 🛠️ ADMIN PANEL 1: PDF UPLOAD & RE-INDEXING ENDPOINT
# =====================================================================
@app.post("/admin/upload-pdf")
async def upload_pdf_and_reindex(
    file: UploadFile = File(...),
    admin_key: str = Form(...)
):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"📄 Saved new PDF: {file.filename}")
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
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    try:
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
AEHSAS Foundation AI Assistant - FastAPI Streaming & Auto-Sync Backend Server
===========================================================================
"""

import os
import time
import asyncio
import shutil
import traceback
from fastapi import FastAPI, Request, Response, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment configuration
from dotenv import load_dotenv
load_dotenv()

from chatbot import stream_chat_response
from feedback import store_unanswered_query, send_error_notification, send_email_alert
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


# =====================================================================
# ⏰ 1. AUTOMATED BACKGROUND SYNC (DAILY CRON JOB)
# =====================================================================
def automated_daily_knowledge_sync():
    """Runs automatically every 24 hours to keep Chroma embeddings synced with live website."""
    print("\n⏰ [CRON JOB STARTED] Running automated daily website sync & embedding refresh...")
    try:
        chunks_added = reindex_website_only()
        print(f"✅ [CRON JOB COMPLETE] Auto-synced knowledge base! Total {chunks_added} chunks refreshed.\n")
        try:
            send_email_alert(
                subject="✅ AEHSAS Chatbot: Daily Knowledge Base Auto-Sync Success",
                body=f"Automated crawler successfully scraped the website and refreshed {chunks_added} chunks in ChromaDB."
            )
        except Exception:
            pass
    except Exception as e:
        print(f"❌ [CRON JOB ERROR] Failed auto-sync: {e}")
        try:
            send_error_notification(
                error_type="AutomatedCronSyncError",
                error_msg=str(e),
                traceback_details=traceback.format_exc()
            )
        except Exception:
            pass

scheduler = BackgroundScheduler()
# automate for every week on sunday at 3:00 AM
# Har hafte Sunday ko raat 3:00 AM par automatically chalega
scheduler.add_job(
    automated_daily_knowledge_sync,
    trigger='cron',
    day_of_week='sun',
    hour=3,
    minute=0
)
scheduler.start()


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

    print(f"\n================ [STREAMING REQUEST] ================")
    print(f"📩 Input: {cleaned_input}")
    print(f"🔑 Session ID: {session_id}")
    print(f"====================================================\n")

    async def token_streamer():
        full_reply = ""
        try:
            for token in stream_chat_response(cleaned_input):
                full_reply += token
                yield token
                await asyncio.sleep(0.005)

            fallback_keywords = [
                "don't know", "don't have information", "not sure", 
                "unable to find", "pata nahi", "sorry, i cannot",
                "does not contain", "cannot answer", "no information", 
                "not available", "not provided", "provided database context", 
                "not mention", "no mention"
            ]
            
            if any(keyword in full_reply.lower() for keyword in fallback_keywords):
                store_unanswered_query(user_query=cleaned_input, session_id=session_id)
                try:
                    subject = f"⚠️ Unanswered Query Alert: Session {session_id}"
                    body = (
                        f"The chatbot encountered a query that is not in the knowledge base.\n\n"
                        f"📌 User Query: {cleaned_input}\n"
                        f"🔑 Session ID: {session_id}\n"
                        f"🤖 Bot Reply: {full_reply}\n"
                    )
                    send_email_alert(subject=subject, body=body)
                except Exception as mail_err:
                    print(f"⚠️ Failed to dispatch unanswered query email alert: {mail_err}")

        except Exception as e:
            tb_str = traceback.format_exc()
            print("\n================ ❌ STREAMING ERROR ❌ ================")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(tb_str)
            print("=======================================================\n")
            
            try:
                send_error_notification(
                    error_type=type(e).__name__,
                    error_msg=str(e),
                    traceback_details=tb_str
                )
            except Exception as mail_err:
                print(f"⚠️ Failed to dispatch error email alert: {mail_err}")
                
            yield "\n[Error: An internal issue occurred while generating the response.]"

    return StreamingResponse(
        token_streamer(),
        media_type="text/plain",
        headers={
            "X-Session-ID": session_id,
            "Cache-Control": "no-cache"
        }
    )


# =====================================================================
# 🌐 2. INSTANT SYNC WEBHOOK (CMS / WEBSITE TRIGGER)
# =====================================================================
@app.post("/webhook/sync-knowledge")
async def trigger_instant_webhook_sync(background_tasks: BackgroundTasks, secret_token: str = Form(...)):
    """Instant webhook URL to automatically re-crawl website when new content is added."""
    if secret_token != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid Webhook Secret")
    
    background_tasks.add_task(reindex_website_only)
    return {
        "status": "processing",
        "message": "Instant auto-sync job started in background! Vector DB will update shortly."
    }


# =====================================================================
# 🛠️ 3. ADMIN PANEL ENDPOINTS
# =====================================================================
@app.post("/admin/upload-pdf")
async def upload_pdf_and_reindex(
    file: UploadFile = File(...),
    admin_key: str = Form(...)
):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"📄 Saved new PDF: {file.filename}")
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


@app.post("/admin/reindex-website")
async def trigger_website_reindex(
    admin_key: str = Form(...)
):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    try:
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

        raise HTTPException(status_code=500, detail=f"Failed to re-index website: {str(e)}")