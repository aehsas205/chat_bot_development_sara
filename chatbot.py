import os
import time
import logging
import traceback
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langgraph.graph.message import add_messages
from google import genai
from langchain_core.messages import AIMessage

from retriever import retrieve_similar_documents
from feedback import handle_feedback  # 👈 Import handle_feedback
from mcp_client import check_and_run_mcp_tools  # 👈 Import non-blocking MCP tool handler

load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

class State(TypedDict):
    messages: Annotated[list, add_messages]

tools = [handle_feedback]

# Load API Key safely
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ CRITICAL WARNING: No GEMINI_API_KEY found in .env file!")

client = genai.Client(api_key=api_key)

def chatmodel(state: State):
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "content"):
        user_query = str(last_message.content)
    elif isinstance(last_message, dict):
        user_query = str(last_message.get("content", ""))
    else:
        user_query = str(last_message)
    
    print("\n" + "="*50)
    print(f"[DEBUG USER QUERY RECEIVED]: '{user_query}'")
    
    # 1. Safe & Fast MCP Tools Check (Non-blocking)
    mcp_extra_context = check_and_run_mcp_tools(user_query)
    if mcp_extra_context:
        print(f"[DEBUG MCP DATA RETRIEVED]: {mcp_extra_context.strip()}")

    # 2. Retrieve Vector DB Context (RAG)
    context = retrieve_similar_documents(user_query)
    print(f"[DEBUG CONTEXT LENGTH RETRIEVED]: {len(context)} characters")
    print("="*50 + "\n")
    
    # Fallback if context is too short
    if not context or len(context) < 20:
        context = retrieve_similar_documents("membership types fees General Member Lifetime Member Patron Special")

    # 3. Combined Prompt for Gemini
    # 3. Combined Prompt for Gemini
    prompt = f"""You are the official AI Assistant for AEHSAS Foundation.
Answer the user question accurately using the provided database context and MCP Tool data below.
If asked about membership, list all membership types, fees, and roles clearly.

CRITICAL LANGUAGE RULE:
Always respond in the EXACT same language and script used by the user in their question:
- If the user asks in Urdu script (e.g., اردو), respond strictly in Urdu script.
- If the user asks in Hindi script (e.g., हिंदी), respond in Hindi script.
- If the user asks in English or Roman script, respond in English or Roman script.

--- CONTEXT FROM DATABASE & TOOLS ---
{context}
{mcp_extra_context}
------------------------------------

User Question: {user_query}
Answer:"""

    try:
        # Standard stable model identifier for Google GenAI SDK
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite", 
            contents=prompt,
            config={"temperature": 0.2}
        )
        answer_text = response.text

    except Exception as e:
        print("\n" + "🚨"*15 + " BACKEND ERROR DETECTED " + "🚨"*15)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        print("-" * 50)
        traceback.print_exc()
        print("🚨"*38 + "\n")
        
        answer_text = "I am having trouble processing your request right now. Please try again."

    return {"messages": [AIMessage(content=answer_text)]}