from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from config import SYSTEM_MESSAGE, get_or_create_session_id
from graph import graph
from config import memory
from contextlib import asynccontextmanager
import asyncio
import time
import logging



class ChatRequest(BaseModel):
    user_input: str

last_access = {}

INACTIVITY_THRESHOLD = 300 
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("aehsas")

async def cleanup_expired_sessions():
    while True:
        logger.debug("clean up task check")
        now = time.time()
        expired_sessions = [
            session_id for session_id, last_seen in last_access.items()
            if now - last_seen > INACTIVITY_THRESHOLD
        ]
        for session_id in expired_sessions:
            try:
                logger.info("Cleaning up expired session: %s", session_id)
                memory.delete_thread(session_id)
                del last_access[session_id]
            except Exception as e:
                logger.warning("Failed to clean session %s: %s", session_id, e)
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm-up RAG pipeline
    logger.info("Warming up the RAG pipeline...")
    try:
        dummy = HumanMessage(content="What is the aehsas foundation?")
        config = {"configurable": {"thread_id": "warmup"}}
        graph.invoke({"messages": [SYSTEM_MESSAGE, dummy]}, config=config)
        logger.info("Warmup complete.")
    except Exception as e:
        logger.warning("Warmup failed: %s", e)
    asyncio.create_task(cleanup_expired_sessions())
    yield
    # Optional shutdown logic here
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://aehsasfoundation.com"],  # <-- Change to your frontend domain
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.head("/health")
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat_endpoint(data: ChatRequest, request: Request, response: Response):
    session_id = get_or_create_session_id(request, response)
    last_access[session_id] = time.time()
    logger.debug("session_id=%s", session_id)
    config = {"configurable": {"thread_id": session_id}}

    user_input = data.user_input.strip()

    user_message = HumanMessage(content=user_input)
    response_obj = graph.invoke({"messages": [SYSTEM_MESSAGE, user_message]}, config=config)
    return {"response": response_obj["messages"][-1].content,"session_id": session_id}
