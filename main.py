from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager

from config import SYSTEM_MESSAGE, get_or_create_session_id, memory
from graph import graph

import asyncio
import time
import logging


# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

logger = logging.getLogger("aehsas")


# ----------------------------
# Request Model
# ----------------------------
class ChatRequest(BaseModel):
    user_input: str


# ----------------------------
# Session Tracking
# ----------------------------
last_access = {}
INACTIVITY_THRESHOLD = 300


# ----------------------------
# Cleanup Inactive Sessions
# ----------------------------
async def cleanup_expired_sessions():
    while True:
        now = time.time()

        expired_sessions = [
            session_id
            for session_id, last_seen in last_access.items()
            if now - last_seen > INACTIVITY_THRESHOLD
        ]

        for session_id in expired_sessions:
            try:
                logger.info("Cleaning session: %s", session_id)

                memory.delete_thread(
                    {"configurable": {"thread_id": session_id}}
                )

                del last_access[session_id]

            except Exception as e:
                logger.warning(e)

        await asyncio.sleep(30)


# ----------------------------
# Warmup
# ----------------------------
async def warmup_task():
    logger.info("Warming up...")

    try:
        dummy = HumanMessage(content="What is AEHSAS Foundation?")

        config = {
            "configurable": {
                "thread_id": "warmup"
            }
        }

        await asyncio.to_thread(
            graph.invoke,
            {"messages": [SYSTEM_MESSAGE, dummy]},
            config=config
        )

        logger.info("Warmup complete.")

    except Exception as e:
        logger.warning(e)


# ----------------------------
# Lifespan
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    # asyncio.create_task(warmup_task())
    asyncio.create_task(cleanup_expired_sessions())

    yield

    logger.info("Shutting down...")


# ----------------------------
# FastAPI
# ----------------------------
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://aehsasfoundation.com"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Health
# ----------------------------
@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}


# ----------------------------
# Frontend
# ----------------------------
@app.get("/", response_class=HTMLResponse)
async def get_index():

    with open("samp.html", "r", encoding="utf-8") as f:
        html = f.read()

    return HTMLResponse(content=html)


# ----------------------------
# Chat Endpoint
# ----------------------------
@app.post("/chat")
async def chat_endpoint(
    data: ChatRequest,
    request: Request,
    response: Response
):

    session_id = get_or_create_session_id(request, response)
    last_access[session_id] = time.time()

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    user_message = HumanMessage(
        content=data.user_input.strip()
    )

    state = graph.get_state(config)

    messages = []

    if (
        not state.values
        or "messages" not in state.values
        or not state.values["messages"]
    ):
        messages.append(SYSTEM_MESSAGE)

    messages.append(user_message)

    # Run LangGraph
    response_obj = await asyncio.to_thread(
        graph.invoke,
        {"messages": messages},
        config=config
    )

    print("\n================ RESPONSE =================")
    print(response_obj)
    print("===========================================")

    last_message = response_obj["messages"][-1]

    print("\nLast message object:")
    print(last_message)

    print("\nContent:")
    print(last_message.content)

    print("\nContent type:")
    print(type(last_message.content))

    # Handle string response
    if isinstance(last_message.content, str):
        reply = last_message.content

    # Handle list response
    elif isinstance(last_message.content, list):

        reply = ""

        for item in last_message.content:

            if isinstance(item, dict):

                if item.get("type") == "text":
                    reply += item.get("text", "")

            else:
                reply += str(item)

    else:
        reply = str(last_message.content)

    print("\nFinal Reply:")
    print(reply)

    return {
        "response": reply,
        "session_id": session_id
    }