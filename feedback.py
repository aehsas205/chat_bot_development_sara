import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Literal
from langchain_core.tools import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@tool
def handle_feedback(feedback_intent: Literal["positive", "negative", "wants_human"]) -> str:
    """Respond to user feedback with appropriate message. Valid feedback types: positive, negative, wants_human."""
    if feedback_intent == "positive":
        return "Glad I could help! Have a great day!"
    elif feedback_intent == "negative":
        return "I'm sorry it wasn't helpful. Would you like to speak to a human representative?"
    elif feedback_intent == "wants_human":
        return "You can fill out this form to contact a human representative: https://aehsasfoundation.com/contact-us"


# --- Unanswered Query Logging & Admin Notification ---

DATA_FILE = "unanswered_queries.json"

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@aehsas.org")


def store_unanswered_query(user_query: str, session_id: str = "default"):
    """Saves unanswered queries into a JSON file and sends an email notification."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "query": user_query,
        "status": "pending_review"
    }

    queries = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                queries = json.load(f)
        except Exception:
            queries = []

    queries.append(entry)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=4)

    send_email_notification(user_query, session_id)


def send_email_notification(user_query: str, session_id: str):
    """Sends email alert when information is missing."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ Missing email credentials in .env. Logged query to JSON only.")
        return

    subject = "🚨 AEHSAS Chatbot Alert: Missing Knowledge Query"
    body = f"Hello Admin,\n\nA user asked a question not found in the knowledge base:\n\nQuery: \"{user_query}\"\nSession: {session_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nPlease update the training data."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # 🔑 FIX: Port 587 with STARTTLS and timeout=10 prevents connection drops
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"📧 Notification sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def send_error_notification(error_type: str = None, error_msg: str = None, traceback_details: str = None):
    """Sends a clean emergency email alert to the admin when an internal error occurs (without raw tracebacks)."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ Skipping error email alert due to missing credentials.")
        return

    subject = "🚨 CRITICAL SYSTEM ERROR: AEHSAS Chatbot Server"
    
    body = (
        "⚠️ ATTENTION ADMIN,\n\n"
        "Chatbot failed because of internal error. "
        "Please take the appropriate action to resolve the issue.\n\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Best regards,\n"
        "AEHSAS Monitoring System"
    )

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # 🔑 FIX: Port 587 with STARTTLS and timeout=10
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"🚨 Clean Emergency Error Alert sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send error email notification: {e}")


def send_email_alert(subject: str, body: str):
    """Generic email alert function used across the app."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ Skipping email alert due to missing credentials.")
        return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # 🔑 FIX: Port 587 with STARTTLS and timeout=10
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"📧 Alert sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send alert email: {e}")