# mcp_client.py
import re

def calculate_donation_impact(amount_inr: float) -> str:
    """Calculates how many meals a donation can sponsor."""
    try:
        meals = int(amount_inr // 50)
        return f"A donation of ₹{amount_inr:.2f} can provide approximately {meals} nutritious meals for underprivileged children."
    except Exception:
        return ""

def get_foundation_helpline() -> str:
    """Returns official helpline for AEHSAS Foundation."""
    return "AEHSAS Foundation Helpline: +91-9876543210 | Email: contact@aehsas.org"

def send_receipt_email(email: str, amount_inr: float) -> str:
    """Simulates sending a donation receipt email."""
    return f"SUCCESS: Donation receipt for ₹{amount_inr:.2f} has been dispatched to {email}."

def calculate_membership_fee(member_type: str, count: int = 1) -> str:
    """Calculates total membership fee."""
    fees = {"general": 500, "lifetime": 5000, "patron": 25000}
    m_type = member_type.lower()
    for key, price in fees.items():
        if key in m_type:
            total = price * count
            return f"Total fee for {count} {key.capitalize()} Membership(s) is ₹{total:,.2f} (Base fee: ₹{price}/person)."
    return "Standard Membership Fee: General = ₹500/yr, Lifetime = ₹5,000, Patron = ₹25,000."

def search_emergency_service(service_type: str) -> str:
    """Handles emergency service requests."""
    return f"EMERGENCY PROTOCOL ACTIVATED for [{service_type.upper()}]: Please call the 24/7 AEHSAS Emergency Desk immediately at +91-9876543210."

def check_and_run_mcp_tools(user_query: str) -> str:
    """Safely checks user query and runs MCP tool logic without blocking the server."""
    extra_context = ""
    query_lower = user_query.lower()
    
    numbers = re.findall(r'\d+', user_query)
    
    # 1. Donation Impact Tool Execution
    if any(keyword in query_lower for keyword in ["donate", "donation", "rs", "₹", "rupees"]) and numbers and "member" not in query_lower:
        try:
            amount = float(numbers[0])
            result = calculate_donation_impact(amount)
            if result:
                extra_context += f"\n[MCP TOOL DATA]: {result}"
        except Exception:
            pass

    # 2. Helpline Tool Execution
    if any(keyword in query_lower for keyword in ["helpline", "contact number", "phone number", "call"]):
        result = get_foundation_helpline()
        extra_context += f"\n[MCP TOOL DATA]: {result}"

    # 3. Receipt Email Tool Execution
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_query)
    if any(keyword in query_lower for keyword in ["receipt", "mail", "send", "email"]) and emails:
        try:
            target_email = emails[0]
            amount = float(numbers[0]) if numbers else 1000.0
            result = send_receipt_email(target_email, amount)
            extra_context += f"\n[MCP TOOL DATA]: {result}"
        except Exception:
            pass

    # 4. Membership Fee Calculation Tool Execution
    if "member" in query_lower or "membership" in query_lower:
        count = int(numbers[0]) if numbers else 1
        m_type = "general"
        if "lifetime" in query_lower:
            m_type = "lifetime"
        elif "patron" in query_lower:
            m_type = "patron"
            
        result = calculate_membership_fee(m_type, count)
        extra_context += f"\n[MCP TOOL DATA]: {result}"

    # 5. Emergency Blood & Health Lookup Tool Execution (NEW)
    if any(keyword in query_lower for keyword in ["blood", "emergency", "ambulance", "hospital", "donor"]):
        service = "Blood / Emergency Service"
        if "blood" in query_lower:
            service = "Blood Requirement"
        elif "ambulance" in query_lower:
            service = "Ambulance Service"
            
        result = search_emergency_service(service)
        extra_context += f"\n[MCP TOOL DATA]: {result}"

    return extra_context


# Testing Block
if __name__ == "__main__":
    print("\n--- 🧪 COMPLETE MCP SUITE SELF-TEST ---")
    test_1 = check_and_run_mcp_tools("If I donate 1000 rs, how many meals?")
    test_2 = check_and_run_mcp_tools("What is the helpline contact number?")
    test_3 = check_and_run_mcp_tools("I donated 2000 rupees, send receipt to test@gmail.com")
    test_4 = check_and_run_mcp_tools("What is the cost for 3 Lifetime memberships?")
    test_5 = check_and_run_mcp_tools("Need emergency A+ blood donor immediately")
    
    print("Test 1 Result:", test_1.strip())
    print("Test 2 Result:", test_2.strip())
    print("Test 3 Result:", test_3.strip())
    print("Test 4 Result:", test_4.strip())
    print("Test 5 Result:", test_5.strip())
    print("---------------------------------------\n")