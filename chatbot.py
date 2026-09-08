""" ================================================
AEHSAS Foundation AI Assistant - Core Chat Model (Streaming Enabled)
================================================"""
import os
import json
import requests
import traceback
from typing import TypedDict, Annotated, Generator
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages
from retriever import retrieve_similar_documents
from feedback import handle_feedback
from mcp_client import check_and_run_mcp_tools
import os

# Google ke global environment credentials ko code level par unset karein
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
os.environ.pop("GCLOUD_PROJECT", None)

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing in .env")

# Direct Gemini 2.5 Flash REST endpoint
STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={API_KEY}"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

class State(TypedDict):
    messages: Annotated[list, add_messages]

tools = [handle_feedback]

def build_prompt(user_query: str) -> str:
    mcp_extra_context = check_and_run_mcp_tools(user_query)
    context = retrieve_similar_documents(user_query)

    return f"""You are the official AI Assistant for AEHSAS Foundation.
Your duty is to answer user queries accurately, completely, and naturally using ONLY the provided context below.

MANDATORY SYNTHESIS RULES:
1. When asked about Core Values or Values of AEHSAS Foundation, list ALL 6 pillars found in the context with brief descriptions.
2. When asked about Milestones or Achievements, list ALL major initiatives found in the context without dropping any.
3. For Vision/Mission, always include the full official multi-sentence paragraph statement.
4. Prioritize information from [SOURCE: LIVE WEBSITE] over [SOURCE: DOCUMENT PDF].
5. NEVER use backend phrases like "provided context", "retrieved chunks", or "database".
6. ONLY show contact information if the requested topic is COMPLETELY ABSENT from the context.
7. If asked to donate, provide UPI Donation ID: `aehsasfound6632@idfcbank`.
8. Respond in the exact same language and script used by the user.

--- CONTEXT FROM DATABASE & TOOLS ---
{context}
{mcp_extra_context}
-------------------------------------

User Question: {user_query}
Answer:"""

def stream_chat_response(user_query: str) -> Generator[str, None, None]:
    """Streams response directly from Gemini REST endpoint via Server-Sent Events (SSE)."""
    prompt = build_prompt(user_query)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }

    try:
        response = requests.post(
            STREAM_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=60
        )

        if response.status_code != 200:
            print(f"Direct API Error {response.status_code}: {response.text}")
            yield (
                "I am currently unable to retrieve this information right now. Please reach out to the AEHSAS Foundation team directly:\n"
                "• Email: connect2aehsas@gmail.com\n"
                "• Phone: +91 8126819192 / +91 8447832604\n"
                "• Contact Form: https://aehsasfoundation.org/contact"
            )
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text_piece = part.get("text", "")
                            if text_piece:
                                yield text_piece
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Error in streaming generation: {e}")
        traceback.print_exc()
        yield (
            "I am currently unable to retrieve this information right now. Please reach out to the AEHSAS Foundation team directly:\n"
            "• Email: connect2aehsas@gmail.com\n"
            "• Phone: +91 8126819192 / +91 8447832604\n"
            "• Contact Form: https://aehsasfoundation.org/contact"
        )

def chatmodel(state: State):
    last_message = state["messages"][-1]
    user_query = str(last_message.content) if hasattr(last_message, "content") else str(last_message)
    prompt = build_prompt(user_query)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }

    try:
        response = requests.post(
            GENERATE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60
        )
        data = response.json()
        answer_text = data["candidates"][0]["content"]["parts"][0]["text"]
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