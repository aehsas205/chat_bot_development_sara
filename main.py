import asyncio
import time
import traceback
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

# Load env variables explicitly
from dotenv import load_dotenv
load_dotenv()

# Import your graph & system message
from graph import graph
from config import SYSTEM_MESSAGE

app = FastAPI()

# Add CORS Middleware to prevent browser connection blocks
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

last_access = {}

def get_or_create_session_id(request: Request, response: Response):
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
    try:
        print(f"\n--- Incoming Request: {data.user_input} ---")
        session_id = data.session_id or request.headers.get("X-Session-ID") or get_or_create_session_id(request, response)
        
        config = {"configurable": {"thread_id": session_id}}
        user_message = HumanMessage(content=data.user_input.strip())

        state = graph.get_state(config)
        messages = []

        if not state.values or "messages" not in state.values or not state.values["messages"]:
            messages.append(SYSTEM_MESSAGE)

        messages.append(user_message)

        # Invoke Graph
        response_obj = await asyncio.to_thread(
            graph.invoke,
            {"messages": messages},
            config=config
        )

        last_message = response_obj["messages"][-1]
        
        if isinstance(last_message.content, str):
            reply = last_message.content
        elif isinstance(last_message.content, list):
            reply = "".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in last_message.content])
        else:
            reply = str(last_message.content)

        return {"response": reply, "session_id": session_id}

    except Exception as e:
        print("\n================ DETAILED BACKEND ERROR ================")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        print("========================================================\n")
        raise HTTPException(status_code=500, detail=str(e))