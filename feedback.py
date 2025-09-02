from typing import Literal
from langchain_core.tools import tool

@tool
def handle_feedback(feedback_intent: Literal["positive", "negative", "wants_human"]) -> str:
    """Respond to user feedback with appropriate message. Valid feedback types: positive, negative, wants_human."""
    if feedback_intent == "positive":
        return "Glad I could help! Have a great day!"
    elif feedback_intent == "negative":
        return "I'm sorry it wasn't helpful. Would you like to speak to a human representative?"
    elif feedback_intent == "wants_human":
        return "You can fill out this form to contact a human representative: https://aehsasfoundation.com/contact-us"
