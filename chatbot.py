""" ================================================
AEHSAS Foundation AI Assistant - Core Chat Model (Streaming Enabled)
================================================"""
import os
import traceback
from typing import TypedDict, Annotated, Generator
from langgraph.graph.message import add_messages
from google import genai
from langchain_core.messages import AIMessage
from retriever import retrieve_similar_documents
from feedback import handle_feedback
from mcp_client import check_and_run_mcp_tools

class State(TypedDict):
    """Represents the state schema for the LangGraph agent chain."""
    messages: Annotated[list, add_messages]

tools = [handle_feedback]

# CLIENT & ENVIRONMENT INITIALIZATION
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def build_prompt(user_query: str) -> str:
    """Helper to fetch MCP tools data, RAG chunks, and format the system prompt."""
    mcp_extra_context = check_and_run_mcp_tools(user_query)
    context = retrieve_similar_documents(user_query)

    return f"""You are the official AI Assistant for AEHSAS Foundation.
Your duty is to answer user queries accurately, completely, and naturally using ONLY the provided context below.

MANDATORY SYNTHESIS RULES:

1. CORE VALUES & PILLARS MANDATE:
   - When asked about Core Values or Values of AEHSAS Foundation, list ALL 6 pillars found in the context (Empowerment Through Access, Equality for Every Voice, Community-Centred Solutions, Transparency and Trust, Collaboration Over Isolation, and Resilience and Sustainability) along with their brief descriptions.

2. MILESTONES & LISTS EXHAUSTIVE DIRECTIVE (NO TRUNCATION):
   - When asked about Milestones or Achievements, you MUST list ALL major initiatives found in the context (including DISHA Career Counselling, Scholarship Distribution, Spoken English Program, Entrance Coaching Interviews, Free Academic Support, School Fee Sponsorship, and Educational Events).
   - Format each milestone as a clear, concise bullet point (2-3 sentences per item) so that NO milestone is dropped or truncated due to length.

3. CORE DEFINITIONS & STATEMENTS:
   - For Vision/Mission, ALWAYS include the full official multi-sentence paragraph statement starting with "To build...", "To empower...", etc.
   - Never output ONLY a short slogan evolution sentence when the main official paragraph is present.

4. LIVE WEBSITE PRIMACY:
   - Always prioritize information from [SOURCE: LIVE WEBSITE] over [SOURCE: DOCUMENT PDF].

5. STRICT ZERO INTERNAL JARGON MANDATE:
   - NEVER use technical or backend phrases like "provided context", "provided information", "based on the context", "context", "database", "retrieved chunks", "PDF snippets", or "backend". Speak as a natural representative of the foundation.

6. MISSING INFORMATION & CONTACT PROTOCOL (STRICT CONDITION):
   - STRICT RULE: Do NOT include, append, or attach any contact details if a valid answer or information is found and provided.
   - ONLY show contact information if the requested topic/detail is COMPLETELY ABSENT from the context.
   - When information is completely missing, NEVER say "the provided context does not contain". State politely that the specific detail is currently not available, followed IMMEDIATELY by the contact details:
     "I am sorry, but specific details regarding [requested topic] are currently not available.

For further information, please contact the AEHSAS Foundation team:
• Email: connect2aehsas@gmail.com
• Phone / WhatsApp: +91 8126819192 / +91 8447832604
• Contact Page: https://aehsasfoundation.org/contact"

7. DONATION & PAYMENT MANDATE:
   - If the user asks how to donate or contribute financially, ALWAYS provide the official UPI Donation ID: `aehsasfound6632@idfcbank`.
   - Provide clear instructions that users can donate using this official UPI ID via any payment app (Google Pay, PhonePe, Paytm etc.).
     UPI DONATION ID: aehsasfound6632@idfcbank

8. BLOGS & ARTICLES DETAILED SUMMARY MANDATE:
- Whenever asked about blogs or articles (e.g., blogs written by Mohsin Anwer or Mohd Faizan), ALWAYS provide complete structured details:
  • Title
  • Author & Designation
  • Date & Read Time / Length
  • Topic Summary (Detailed explanation of the blog content)

9. Respond in the exact same language and script used by the user.

--- CONTEXT FROM DATABASE & TOOLS ---
{context}
{mcp_extra_context}
-------------------------------------

User Question: {user_query}
Answer:"""

# ⚡ REAL-TIME TOKEN STREAMING GENERATOR
def stream_chat_response(user_query: str) -> Generator[str, None, None]:
    """Yields token chunks word-by-word in real time as they arrive from Gemini."""
    prompt = build_prompt(user_query)
    try:
        response_stream = client.models.generate_content_stream(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 2048
            }
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Error in streaming generation: {e}")
        traceback.print_exc()
        yield (
            "I am currently unable to retrieve this information right now. Please reach out to the AEHSAS Foundation team directly:\n"
            "• Email: connect2aehsas@gmail.com\n"
            "• Phone: +91 8126819192 / +91 8447832604\n"
            "• Contact Form: https://aehsasfoundation.org/contact"
        )

# STANDARD BATCH FALLBACK (For non-streaming calls)
def chatmodel(state: State):
    last_message = state["messages"][-1]
    user_query = str(last_message.content) if hasattr(last_message, "content") else str(last_message)
    prompt = build_prompt(user_query)

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 2048
            }
        )
        answer_text = response.text
    except Exception as e:
        print(f"Error in chatmodel execution: {e}")
        traceback.print_exc()
        answer_text = (
            "I am currently unable to retrieve this information right now. Please reach out to the AEHSAS Foundation team directly:\n"
            "• Email: connect2aehsas@gmail.com\n"
            "• Phone: +91 8126819192 / +91 8447832604\n"
            "• Contact Form: https://aehsasfoundation.org/contact"
        )

    return {"messages": [AIMessage(content=answer_text)]}