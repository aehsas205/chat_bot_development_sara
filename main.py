import os
import time
import asyncio
import traceback
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv()

from graph import graph
from feedback import store_unanswered_query, send_error_notification, send_email_alert

app = FastAPI(title="AEHSAS Foundation Chatbot API")

# CORS Setup
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

# Absolute path resolution for Render deployment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "samp.html")

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

        # Invoke LangGraph
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
            "does not contain", "cannot answer", "no information", "not available", "not provided", "provided database context"
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