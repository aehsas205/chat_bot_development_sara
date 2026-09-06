import os
import io
import json
import fitz  # PyMuPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AEHSAS Helper Tools")

# ----------------- GOOGLE DRIVE CONFIG -----------------
SERVICE_ACCOUNT_FILE = "google_credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
PROCESSED_TRACKER_FILE = "processed_drive_files.json"

def _get_drive_client():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def _get_processed_ids() -> set:
    if os.path.exists(PROCESSED_TRACKER_FILE):
        try:
            with open(PROCESSED_TRACKER_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def _save_processed_id(file_id: str):
    ids = _get_processed_ids()
    ids.add(file_id)
    with open(PROCESSED_TRACKER_FILE, "w") as f:
        json.dump(list(ids), f, indent=2)

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
    fees = {"general": 250, "lifetime": 501, "patron": 1001, "position holder": 250}
    m_type = member_type.lower()
    for key, price in fees.items():
        if key in m_type:
            total = price * count
            return f"Total fee for {count} {key.capitalize()} Membership(s) is ₹{total:,.2f} (Base fee: ₹{price}/person)."
    return "Standard Membership Fee: General = ₹250/yr, Lifetime = ₹201, Patron = ₹1001, Position Holder = ₹250."

# Tool 5: Emergency Blood & Health Lookup
@mcp.tool()
def search_emergency_service(service_type: str) -> str:
    """Handles emergency medical and blood requests."""
    return f"EMERGENCY PROTOCOL ACTIVATED for [{service_type.upper()}]: Please call the 24/7 AEHSAS Emergency Desk immediately at +91-9876543210 or visit the nearest helpline camp."

# Tool 6: Google Drive Auto PDF Extractor (NEW MCP TOOL)
@mcp.tool()
def sync_drive_documents(folder_id: str) -> str:
    """
    Scans a specific Google Drive folder for newly added PDFs, extracts 
    full text content via PyMuPDF in-memory, and returns the documents JSON.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        return json.dumps({"error": f"Credentials file '{SERVICE_ACCOUNT_FILE}' not found."})

    try:
        service = _get_drive_client()
        processed_ids = _get_processed_ids()

        query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
        response = service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get('files', [])

        extracted_docs = []

        for f in files:
            f_id = f['id']
            f_name = f['name']

            if f_id in processed_ids:
                continue

            # Download PDF in-memory
            req = service.files().get_media(fileId=f_id)
            stream = io.BytesIO()
            downloader = MediaIoBaseDownload(stream, req)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            stream.seek(0)
            doc = fitz.open(stream=stream.read(), filetype="pdf")
            
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"

            if full_text.strip():
                extracted_docs.append({
                    "file_id": f_id,
                    "file_name": f_name,
                    "content": full_text.strip(),
                    "source": f"GoogleDrive/{f_name}"
                })
                _save_processed_id(f_id)

        return json.dumps({
            "status": "success",
            "new_files_count": len(extracted_docs),
            "documents": extracted_docs
        })

    except Exception as e:
        return json.dumps({"error": f"Drive sync failed: {str(e)}"})

if __name__ == "__main__":
    mcp.run()