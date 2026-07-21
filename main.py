import asyncio
import time
import traceback
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

# Load env variables explicitly
from dotenv import load_dotenv
load_dotenv()

# Import graph & system message
from graph import graph
from config import SYSTEM_MESSAGE

app = FastAPI(title="AEHSAS Foundation Chatbot API")

# CORS Middleware setup
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

def get_or_create_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = f"session_{int(time.time() * 1000)}"
        response.set_cookie(key="session_id", value=session_id)
    return session_id

@app.get("/")
async def serve_frontend():
    return FileResponse("samp.html")

@app.post("/chat")
async def chat_endpoint(data: ChatRequest, request: Request, response: Response):
    # 1. Validation: Empty input or whitespace handling
    cleaned_input = data.user_input.strip() if data.user_input else ""
    if not cleaned_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    try:
        print(f"\n--- Incoming Request: {cleaned_input} ---")
        session_id = data.session_id or request.headers.get("X-Session-ID") or get_or_create_session_id(request, response)
        
        config = {"configurable": {"thread_id": session_id}}
        user_message = HumanMessage(content=cleaned_input)

        state = graph.get_state(config)
        messages = []

        if not state.values or "messages" not in state.values or not state.values["messages"]:
            messages.append(SYSTEM_MESSAGE)

        messages.append(user_message)

        # 2. Invoke Graph with error handling
        response_obj = await asyncio.to_thread(
            graph.invoke,
            {"messages": messages},
            config=config
        )

        # Safety Check: Response Validation
        if not response_obj or "messages" not in response_obj or not response_obj["messages"]:
            raise ValueError("Invalid or empty response returned from Graph pipeline.")

        last_message = response_obj["messages"][-1]
        
        # Format message content cleanly
        if isinstance(last_message.content, str):
            reply = last_message.content
        elif isinstance(last_message.content, list):
            reply = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in last_message.content])
        else:
            reply = str(last_message.content)

        return {"response": reply, "session_id": session_id}

    except HTTPException as http_exc:
        # Re-raise explicit HTTP exceptions (like 400 Bad Request)
        raise http_exc

    except Exception as e:
        # 3. Log detailed internal errors in Terminal for debugging
        print("\n================ DETAILED BACKEND ERROR ================")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        print("========================================================\n")
        
        # User-friendly response to client (Prevents raw code stack trace exposure)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again later."
        )