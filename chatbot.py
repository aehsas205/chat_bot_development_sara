import os
import time
import logging
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langgraph.graph.message import add_messages
import google.generativeai as genai
from langchain_core.messages import AIMessage

from retriever import retrieve_similar_documents
from feedback import handle_feedback

load_dotenv()

log = logging.getLogger("aehsas")

class State(TypedDict):
    messages: Annotated[list, add_messages]

# Dummy/Placeholder list taaki graph.py ka import crash na ho
tools = []

# Google GenAI Client
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

def chatmodel(state: State):
    t0 = time.time()
    
    # User ka last message extract karein
    last_message = state["messages"][-1]
    user_query = getattr(last_message, "content", str(last_message))
    
    # 1. ChromaDB database se information retrieve karein
    context = retrieve_similar_documents(user_query)
    
    # 2. Complete Context Prompt compose karein
    prompt = f"""You are an AI Assistant for AEHSAS Foundation.
Use the following retrieved context from the database to answer the user question accurately.

Context:
{context}

Question: {user_query}
"""

    # 3. Direct Google GenAI API Call (No Langchain 404/v1beta bugs)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    t1 = time.time()
    log.info("[LLM] %.3fs model=gemini-2.5-flash", (t1 - t0))
    
    return {"messages": state["messages"] + [AIMessage(content=response.text)]}