import os
import io
import re
import json
import fitz  # PyMuPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

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


# ----------------- EXISTING TOOLS (1 - 5) -----------------
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
    fees = {"general": 250, "lifetime": 501, "patron": 1001, "position holder": 250}
    m_type = member_type.lower()
    for key, price in fees.items():
        if key in m_type:
            total = price * count
            return f"Total fee for {count} {key.capitalize()} Membership(s) is ₹{total:,.2f} (Base fee: ₹{price}/person)."
    return "Standard Membership Fee: General = ₹250/yr, Lifetime = ₹201, Patron = ₹1001, Position Holder = ₹250."
    
def search_emergency_service(service_type: str) -> str:
    """Handles emergency service requests."""
    return f"EMERGENCY PROTOCOL ACTIVATED for [{service_type.upper()}]: Please call the 24/7 AEHSAS Emergency Desk immediately at +91-9876543210."


# ----------------- NEW TOOL 6: GOOGLE DRIVE SYNC -----------------
def sync_drive_documents(folder_id: str) -> dict:
    """
    Checks Google Drive folder for unindexed PDFs, extracts text via PyMuPDF,
    and returns a structured list of documents with source metadata.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        return {"error": f"Credentials file '{SERVICE_ACCOUNT_FILE}' not found. Please place it in project root."}

    try:
        service = _get_drive_client()
        processed_ids = _get_processed_ids()

        query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
        response = service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get('files', [])

        new_documents = []

        for f in files:
            f_id = f['id']
            f_name = f['name']

            if f_id in processed_ids:
                continue

            # In-memory download (no temp clutter)
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
                new_documents.append({
                    "file_id": f_id,
                    "file_name": f_name,
                    "content": full_text.strip(),
                    "source": f"GoogleDrive/{f_name}"
                })
                _save_processed_id(f_id)

        return {
            "status": "success",
            "new_files_count": len(new_documents),
            "documents": new_documents
        }

    except Exception as e:
        return {"error": f"Drive sync failed: {str(e)}"}


# ----------------- RUNNER FOR RUNTIME QUERIES -----------------
def check_and_run_mcp_tools(user_query: str) -> str:
    """Safely checks user query and runs runtime MCP tool logic."""
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

    # 5. Emergency Blood & Health Lookup Tool Execution
    if any(keyword in query_lower for keyword in ["blood", "emergency", "ambulance", "hospital", "donor"]):
        service = "Blood / Emergency Service"
        if "blood" in query_lower:
            service = "Blood Requirement"
        elif "ambulance" in query_lower:
            service = "Ambulance Service"
            
        result = search_emergency_service(service)
        extra_context += f"\n[MCP TOOL DATA]: {result}"

    return extra_context


# ----------------- PIPELINE HELPER FOR CHROMA INGESTION -----------------
def execute_drive_ingestion(folder_id: str, vectorstore, text_splitter) -> str:
    """
    Extracts new PDFs via MCP Drive Tool, chunks text, and pushes embeddings to ChromaDB.
    """
    result = sync_drive_documents(folder_id)
    
    if "error" in result:
        return f"❌ Ingestion Error: {result['error']}"
        
    docs = result.get("documents", [])
    if not docs:
        return "ℹ️ No new PDF documents found in Drive folder."
        
    total_chunks = 0
    for doc in docs:
        chunks = text_splitter.split_text(doc["content"])
        metadatas = [{"source": doc["source"], "file_id": doc["file_id"]} for _ in chunks]
        vectorstore.add_texts(texts=chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        
    return f"✅ Successfully ingested {len(docs)} new PDF(s) ({total_chunks} total chunks) into ChromaDB."


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
    
    # Test Drive Tool Syntax (Pass your folder id to test live)
    print("\nTesting Drive Tool Syntax...")
    drive_test = sync_drive_documents("107axMbDQ6nz0vJx9IKYmpswy6a27f1kQ")
    print("Drive Check Status:", drive_test.get("error") or drive_test.get("status"))
    print("---------------------------------------\n")