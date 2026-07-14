from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from retriever import retrieve_similar_documents
from feedback import handle_feedback
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
import time
import logging


load_dotenv()

model="gemini-3.1-flash-lite"
model_provider="google_genai"
log = logging.getLogger("aehsas")

class State(TypedDict):
    messages: Annotated[list, add_messages]

# List of tools the chatbot can call
tools = [retrieve_similar_documents,handle_feedback]



llm = init_chat_model(
    model=model,
    model_provider=model_provider,
    temperature=0.1
).bind_tools(tools)



def chatmodel(state: State):
    t0=time.time()
    output = llm.invoke(state["messages"])
    t1=time.time()
    log.info("[LLM] %.3fs model=%s", (t1 - t0), model)
    return {"messages": state["messages"] + [output]}
