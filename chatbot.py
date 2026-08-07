import os
import traceback
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from google import genai
from langchain_core.messages import AIMessage
from retriever import retrieve_similar_documents
from feedback import handle_feedback
from mcp_client import check_and_run_mcp_tools

class State(TypedDict):
    """Represents the state schema for the LangGraph agent chain."""
    messages: Annotated[list, add_messages]

# CRITICAL EXPORT: Exported tools list required by graph.py
tools = [handle_feedback]

api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def chatmodel(state: State):
    """
    Core AI execution function with dynamic context retrieval and source prioritization.
    Enforces website primacy over stale PDF text and ensures complete non-truncated lists.
    """
    last_message = state["messages"][-1]
    user_query = str(last_message.content) if hasattr(last_message, "content") else str(last_message)
    
    mcp_extra_context = check_and_run_mcp_tools(user_query)
    context = retrieve_similar_documents(user_query)

    prompt = f"""You are the official AI Assistant for AEHSAS Foundation.
Your primary duty is to answer the user's question accurately using ONLY the retrieved context and tool data provided below.

1. ABSOLUTE ZERO TECHNICAL JARGON RULE (NON-TECHNICAL USER LANGUAGE):
   - NEVER mention internal technical terms in your responses to users.
   - Strictly avoid words like: "retrieved context", "context", "database", "PDF snippets", "chunks", "knowledge base", "vectorstore", "URL", or "backend".
   - Express all information naturally, smoothly, and warmly as an official representative of AEHSAS Foundation.

2. MISSING INFORMATION & DIRECT AEHSAS CONTACT PROTOCOL:
   - If the requested information is not available in the provided data below, state clearly and politely that the information is not currently available.
   - ALWAYS invite the user to connect directly with the AEHSAS Foundation team for further details.
   - You MUST include the following official contact channels whenever answering queries that lack available data:
     • Email: connect2aehsas@gmail.com
     • Phone / WhatsApp: +91 8126819192 / +91 8447832604
     • Contact Page: https://aehsasfoundation.org/contact

CRITICAL SOURCE HIERARCHY & PREFERENCE RULES:
3. WEBSITE PRIMACY: The retrieved context contains snippets marked as [SOURCE: LIVE WEBSITE] and [SOURCE: DOCUMENT PDF].
   - Whenever there is ANY contradiction or conflict between Live Website snippets and PDF snippets (e.g. names listed on the website vs "names not listed" in older PDF text), ALWAYS treat the LIVE WEBSITE data as the SINGLE SOURCE OF TRUTH.
   - NEVER state that names or details are "not listed" or "not explicitly mentioned" if they appear anywhere on a Live Website snippet.

4. COMPREHENSIVE LISTING MANDATE (ZERO OMISSION):
   - When asked about founders, post holders, milestones, programs, or initiatives, extract EVERY SINGLE item, individual, title, and program found across the context (including DISHA Career Counselling, Spoken English Program, Scholarship Distribution, etc.).
   - Do NOT shorten, summarize, or omit any listed milestone, program, or coordinator.
   - Present all items in a clean, natural list directly in the main response.
   - Always clearly distinguish between CURRENT post holders/programs and FORMER incumbents if both are present in the context.
5. UPI ID for donation is: aehsasfound6632@idfcbank

6. EXACT LANGUAGE SCRIPT RULE:
   - Always respond in the EXACT same language and script used by the user in their question (e.g., Urdu script, Hindi script, English, or Roman script).

--- CONTEXT FROM DATABASE & TOOLS ---
{context}
{mcp_extra_context}
-------------------------------------

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
        print(f"Error in chatmodel execution: {e}")
        traceback.print_exc()
        answer_text = ("I am currently unable to retrieve this information right now. Please reach out to the AEHSAS Foundation team directly:\n"
            "• Email: connect2aehsas@gmail.com\n"
                        )

    return {"messages": [AIMessage(content=answer_text)]}