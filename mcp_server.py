# mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AEHSAS Helper Tools")

# Tool 1: Donation Impact
@mcp.tool()
def calculate_donation_impact(amount_inr: float) -> str:
    """Calculates how many meals a donation can sponsor."""
    try:
        meals = int(amount_inr // 50)
        return f"A donation of ₹{amount_inr:.2f} can provide approximately {meals} nutritious meals for underprivileged children."
    except Exception as e:
        return f"Error: {str(e)}"

# Tool 2: Helpline Info
@mcp.tool()
def get_foundation_helpline() -> str:
    """Returns official helpline for AEHSAS Foundation."""
    return "AEHSAS Foundation Helpline: +91-9876543210 | Email: contact@aehsas.org"

# Tool 3: Receipt Email Simulation
@mcp.tool()
def send_receipt_email(email: str, amount_inr: float) -> str:
    """Simulates sending a donation receipt email."""
    return f"SUCCESS: Donation receipt for ₹{amount_inr:.2f} has been dispatched to {email}."

# Tool 4: Membership Fee Calculator
@mcp.tool()
def calculate_membership_fee(member_type: str, count: int = 1) -> str:
    """Calculates total fee for given membership type and count."""
    fees = {"general": 500, "lifetime": 5000, "patron": 25000}
    m_type = member_type.lower()
    for key, price in fees.items():
        if key in m_type:
            total = price * count
            return f"Total fee for {count} {key.capitalize()} Membership(s) is ₹{total:,.2f} (Base fee: ₹{price}/person)."
    return "Standard Membership Fee: General = ₹500/yr, Lifetime = ₹5,000, Patron = ₹25,000."

# Tool 5: Emergency Blood & Health Lookup (NEW TOOL)
@mcp.tool()
def search_emergency_service(service_type: str) -> str:
    """Handles emergency medical and blood requests."""
    return f"EMERGENCY PROTOCOL ACTIVATED for [{service_type.upper()}]: Please call the 24/7 AEHSAS Emergency Desk immediately at +91-9876543210 or visit the nearest helpline camp."

if __name__ == "__main__":
    mcp.run()