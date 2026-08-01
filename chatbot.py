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
from feedback import handle_feedback
from mcp_client import check_and_run_mcp_tools

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

# Initialize Google GenAI Client
client = genai.Client(api_key=api_key)

def chatmodel(state: State):
    """
    Core Chat Model function for LangGraph node execution.
    Extracts user prompt, runs MCP tools, retrieves vector context with team expansion,
    and invokes Gemini with strict language and completeness mandates.
    """
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
    
    # Double-check and expand context if question pertains to team members / post holders
    team_keywords = [
        "post holder", "post-holder", "office bearer", "office-bearer", 
        "team", "executive", "director", "coordinator", "leadership", 
        "members", "who are", "incumbents", "roster"
    ]
    query_lower = user_query.lower()
    if any(k in query_lower for k in team_keywords):
        team_extra_context = retrieve_similar_documents(
            "AEHSAS Foundation team post holders members executives coordinators directors leadership "
            "President Secretary Treasurer Program Manager Executive Director Event Coordinator "
            "Marketing Coordinator R&D Coordinator Mohsin Anwer Mohd Faizan Rizwan Ahmad Saifi "
            "Faisal Jawahar Mohammad Azeem Khan Nafees Ahmad Mohsin Azmi Muhammad Arhab"
        )
        if team_extra_context and team_extra_context not in context:
            context = context + "\n\n--- ADDITIONAL TEAM ROSTER CONTEXT ---\n\n" + team_extra_context

    # 3. Combined Prompt for Gemini
    prompt = f"""You are the official AI Assistant for AEHSAS Foundation.
Answer the user question accurately using the provided database context and MCP Tool data below.

CRITICAL ROSTER & POST-HOLDER MANDATE:
- When asked about "Post Holders", "Office Bearers", "Executive Team", or "Team Members", list EVERY SINGLE person and designation mentioned in the context.
- Include ALL 8+ positions: 
  1. President (Mohsin Anwer)
  2. Secretary (Mohd Faizan)
  3. Treasurer (Rizwan Ahmad Saifi)
  4. Program Manager (Faisal Jawahar)
  5. Executive Director (Mohammad Azeem Khan)
  6. Event Coordinator (Nafees Ahmad)
  7. Marketing Coordinator (Mohsin Azmi)
  8. Assistant R&D Coordinator (Muhammad Arhab)
  ...and any other team member found in the context.
- Do NOT restrict the list to only President, Secretary, and Treasurer.
- Do NOT relegate any coordinator, director, or manager to a footnote or generic note. Put EVERY individual directly into the main bulleted response list with their complete title and details.

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
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite", 
            contents=prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 2048
            }
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