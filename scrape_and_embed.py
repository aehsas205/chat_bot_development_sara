"""
AEHSAS Foundation AI Assistant - Data Scraping, Google Drive Sync & Embedding Engine
===================================================================================
"""

import os
import io
import json
import shutil
import glob
import time
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore, CHROMA_PATH

# Google Drive API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

PROCESSED_TRACKER_FILE = "processed_drive_files.json"
CREDENTIALS_FILE = "google_credentials.json"
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
UPLOADS_DIR = "uploads"

os.makedirs(UPLOADS_DIR, exist_ok=True)

# ==========================================
# 1. VECTORSTORE MANAGEMENT UTILITY
# ==========================================

def clear_vectorstore():
    """Wipes the existing Chroma database before re-indexing to purge obsolete cache."""
    if os.path.exists(CHROMA_PATH):
        try:
            shutil.rmtree(CHROMA_PATH)
            print(" Old Chroma database vectorstore cleared successfully!")
        except Exception as e:
            print(f" Warning clearing vectorstore: {e}")

# ==========================================
# 2. GOOGLE DRIVE SYNC ENGINE
# ==========================================

def load_processed_files() -> list:
    """Loads list of already embedded file IDs."""
    if os.path.exists(PROCESSED_TRACKER_FILE):
        try:
            with open(PROCESSED_TRACKER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_processed_files(file_ids: list):
    """Saves updated list of processed file IDs."""
    with open(PROCESSED_TRACKER_FILE, "w") as f:
        json.dump(file_ids, f, indent=4)

def sync_and_download_new_drive_files() -> list:
    """
    Checks Google Drive folder for new/unprocessed PDF files,
    downloads them into the uploads/ directory, and returns their paths.
    """
    if not DRIVE_FOLDER_ID:
        print(" GOOGLE_DRIVE_FOLDER_ID not set in .env. Skipping Drive sync.")
        return []

    if not os.path.exists(CREDENTIALS_FILE):
        print(f" Credentials file '{CREDENTIALS_FILE}' not found. Skipping Drive sync.")
        return []

    print(" Checking Google Drive for newly added documents...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        service = build("drive", "v3", credentials=creds)

        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false and mimeType = 'application/pdf'"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        drive_files = results.get("files", [])

        processed_ids = load_processed_files()
        new_downloaded_paths = []

        for f in drive_files:
            file_id = f["id"]
            file_name = f["name"]

            if file_id not in processed_ids:
                print(f"📥 New Drive file found: '{file_name}' (ID: {file_id}). Downloading...")
                file_dest = os.path.join(UPLOADS_DIR, file_name)

                request = service.files().get_media(fileId=file_id)
                with io.FileIO(file_dest, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                processed_ids.append(file_id)
                new_downloaded_paths.append(file_dest)
                print(f" Downloaded '{file_name}' to '{file_dest}'")

        save_processed_files(processed_ids)
        return new_downloaded_paths

    except Exception as e:
        print(f"❌ Error during Google Drive synchronization: {e}")
        return []

# ==========================================
# 3. WEB CRAWLING & DYNAMIC SCRAPING ENGINE
# ==========================================

def discover_all_website_urls(base_url: str = "https://aehsasfoundation.org") -> list:
    visited_urls = set()
    to_visit = {base_url, f"{base_url}/"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    for _ in range(2):
        current_batch = list(to_visit - visited_urls)
        for url in current_batch:
            visited_urls.add(url)
            try:
                response = requests.get(url, headers=headers, timeout=8)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"].strip()
                        full_url = urljoin(base_url, href)
                        parsed = urlparse(full_url)
                        if parsed.netloc == urlparse(base_url).netloc:
                            clean_url = full_url.split("#")[0].rstrip("/")
                            if clean_url and not any(clean_url.endswith(ext) for ext in [".pdf", ".png", ".jpg", ".jpeg", ".svg"]):
                                to_visit.add(clean_url)
            except Exception as e:
                print(f"  Crawler notice fetching links from {url}: {e}")

    fallback_urls = [
        f"{base_url}/", f"{base_url}/about", f"{base_url}/about-us",
        f"{base_url}/our-team", f"{base_url}/founding-members",
        f"{base_url}/post-incumbents", f"{base_url}/former-incumbents",
        f"{base_url}/patrons", f"{base_url}/contact", f"{base_url}/our-work",
        f"{base_url}/milestones", f"{base_url}/donate", f"{base_url}/membership",
        f"{base_url}/press-releases", f"{base_url}/careers",
        f"{base_url}/privacy-policy", f"{base_url}/license",
        f"{base_url}/tc", f"{base_url}/blog"
    ]
    for fallback in fallback_urls:
        to_visit.add(fallback.rstrip("/"))

    final_url_list = list(to_visit)
    print(f" Auto-Discovered {len(final_url_list)} unique internal website pages to scrape.")
    return final_url_list

def fetch_web_document_dynamic(url: str) -> Document:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        element.decompose()

    page_title = soup.title.string.strip() if soup.title and soup.title.string else url
    raw_lines = soup.get_text(separator="\n").splitlines()
    cleaned_lines = [line.strip() for line in raw_lines if line.strip() and "JavaScript" not in line]

    full_text = f"Live Website Content Page: {page_title} ({url})\n" + "\n".join(cleaned_lines)

    return Document(
        page_content=full_text,
        metadata={
            "source": url,
            "title": url,
            "is_website": True,
            "priority": 1
        }
    )

# ==========================================
# 4. PROCESSING & EMBEDDING PIPELINE
# ==========================================

def process_and_embed_all():
    """Full indexing: Syncs Drive, scrapes website, and embeds everything into ChromaDB."""
    clear_vectorstore()
    documents = []

    # 1. Sync from Google Drive
    sync_and_download_new_drive_files()

    # 2. Scrape Website
    urls = discover_all_website_urls()
    print(f" Fetching live website pages ({len(urls)} URLs)...")
    for url in urls:
        try:
            doc = fetch_web_document_dynamic(url)
            if len(doc.page_content) > 80:
                documents.append(doc)
        except Exception as e:
            print(f"  Skipping {url}: {e}")

    # 3. Process Local PDFs (including downloaded Drive files)
    pdf_files = glob.glob("*.pdf") + glob.glob("uploads/*.pdf")
    for pdf_path in pdf_files:
        try:
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            for p_doc in pdf_docs:
                p_doc.metadata["source"] = pdf_path
                p_doc.metadata["is_website"] = False
                p_doc.metadata["priority"] = 2
            documents.extend(pdf_docs)
            print(f"   PDF '{pdf_path}' processed successfully!")
        except Exception as e:
            print(f"   PDF processing error for {pdf_path}: {e}")

    if not documents:
        print(" No documents found to embed!")
        return 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=600
    )
    chunks = text_splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)

    print(f" Success! Embedded total {len(chunks)} chunks into ChromaDB.")
    return len(chunks)

def sync_drive_incremental():
    """
    Lightweight sync: Downloads ONLY newly added Drive files and embeds them
    without re-scraping the entire website or wiping the database.
    """
    new_files = sync_and_download_new_drive_files()
    if not new_files:
        print(" No new Drive documents to process.")
        return 0

    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=600
    )

    for pdf_path in new_files:
        try:
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            for p_doc in pdf_docs:
                p_doc.metadata["source"] = pdf_path
                p_doc.metadata["is_website"] = False
                p_doc.metadata["priority"] = 2

            chunks = text_splitter.split_documents(pdf_docs)
            all_chunks.extend(chunks)
            print(f" Prepared {len(chunks)} chunks from '{pdf_path}'.")
        except Exception as e:
            print(f"❌ Failed to process '{pdf_path}': {e}")

    if all_chunks:
        vectorstore = get_vectorstore()
        vectorstore.add_documents(all_chunks)
        print(f" Added {len(all_chunks)} new chunks to ChromaDB!")

    return len(all_chunks)

def process_and_embed_pdf(pdf_path: str):
    """Processes and embeds a single uploaded PDF file into ChromaDB."""
    try:
        print(f"📄 Processing uploaded PDF: {pdf_path}...")
        loader = PyPDFLoader(pdf_path)
        pdf_docs = loader.load()
        for p_doc in pdf_docs:
            p_doc.metadata["source"] = pdf_path
            p_doc.metadata["is_website"] = False
            p_doc.metadata["priority"] = 2

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=5000,
            chunk_overlap=600
        )
        chunks = text_splitter.split_documents(pdf_docs)

        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)
        print(f"✅ Successfully embedded {len(chunks)} chunks from '{pdf_path}'.")
        return len(chunks)
    except Exception as e:
        print(f"❌ Error processing PDF '{pdf_path}': {e}")
        return 0

def reindex_website_only():
    """Re-scrapes website pages dynamically and updates ChromaDB."""
    print("🔄 Triggering Admin Website Re-indexing...")
    return process_and_embed_all()

if __name__ == "__main__":
    # Test Drive incremental sync
    sync_drive_incremental()