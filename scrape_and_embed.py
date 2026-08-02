import os
import shutil
import glob
import time
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore, CHROMA_PATH

def clear_vectorstore():
    """Wipes the existing Chroma database before re-indexing to purge obsolete cache."""
    if os.path.exists(CHROMA_PATH):
        try:
            shutil.rmtree(CHROMA_PATH)
            print("🧹 Old Chroma database vectorstore cleared successfully!")
        except Exception as e:
            print(f"⚠️ Warning clearing vectorstore: {e}")

def get_website_urls():
    """List of all official AEHSAS Foundation website pages to scrape."""
    base_url = "https://aehsasfoundation.org"
    return [
        f"{base_url}/",
        f"{base_url}/about",
        f"{base_url}/about-us",
        f"{base_url}/our-team",
        f"{base_url}/team",
        f"{base_url}/leadership",
        f"{base_url}/founding-members",
        f"{base_url}/post-incumbents",
        f"{base_url}/former-incumbents",
        f"{base_url}/patrons",
        f"{base_url}/contact",
        f"{base_url}/our-work",
        f"{base_url}/milestones",
        f"{base_url}/donate",
        f"{base_url}/membership"
    ]

def fetch_web_document_dynamic(url: str) -> Document:
    """
    Fetches text content from dynamic React SPAs.
    Tries Selenium Headless Chrome rendering first, falling back to Requests/BS4.
    """
    html_content = ""
    
    # Attempt 1: Selenium Headless Browser for React JS rendering
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(2)  # Wait for React components to mount and populate DOM
        html_content = driver.page_source
        driver.quit()
    except Exception:
        # Fallback to standard HTTP requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Clean irrelevant boilerplate tags
    for element in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        element.decompose()

    page_title = soup.title.string.strip() if soup.title and soup.title.string else url
    raw_lines = soup.get_text(separator="\n").splitlines()
    cleaned_lines = [line.strip() for line in raw_lines if line.strip() and "JavaScript" not in line]
    
    full_text = f"Live Website Content Page: {page_title} ({url})\n" + "\n".join(cleaned_lines)
    
    # Tagging metadata with is_website=True for source priority ranking
    return Document(
        page_content=full_text,
        metadata={
            "source": url, 
            "title": page_title,
            "is_website": True,
            "priority": 1
        }
    )

def process_and_embed_all():
    """
    Clears existing vector DB, dynamically scrapes all website URLs (handling React JS),
    processes local PDF files, and embeds chunks into ChromaDB with source priority tags.
    """
    clear_vectorstore()
    documents = []
    
    # 1. Scrape Live Website Content
    urls = get_website_urls()
    print(f"🌐 Fetching live website pages ({len(urls)} URLs)...")
    for url in urls:
        try:
            doc = fetch_web_document_dynamic(url)
            if len(doc.page_content) > 80:
                documents.append(doc)
                print(f"  ✅ Dynamically Scraped Website Page: {url}")
        except Exception as e:
            print(f"  ⚠️ Skipping {url}: {e}")

    # 2. Add Local Document PDFs
    pdf_files = glob.glob("*.pdf") + glob.glob("uploads/*.pdf")
    for pdf_path in pdf_files:
        try:
            print(f"📄 Processing PDF File: {pdf_path}...")
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            for p_doc in pdf_docs:
                p_doc.metadata["source"] = pdf_path
                p_doc.metadata["is_website"] = False
                p_doc.metadata["priority"] = 2
            documents.extend(pdf_docs)
            print(f"  ✅ PDF '{pdf_path}' processed successfully!")
        except Exception as e:
            print(f"  ⚠️ PDF processing error for {pdf_path}: {e}")

    if not documents:
        print("⚠️ No documents found to embed!")
        return 0

    # Split into structured chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=500
    )
    chunks = text_splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    print(f"🎉 Success! Embedded total {len(chunks)} chunks into ChromaDB.")
    return len(chunks)

def process_and_embed_pdf(pdf_path: str):
    """
    Processes a single newly uploaded PDF file from the Admin endpoint
    and appends its text chunks into the existing ChromaDB vector store.
    """
    try:
        print(f"📄 Processing newly uploaded PDF: {pdf_path}...")
        loader = PyPDFLoader(pdf_path)
        pdf_docs = loader.load()
        for p_doc in pdf_docs:
            p_doc.metadata["source"] = pdf_path
            p_doc.metadata["is_website"] = False
            p_doc.metadata["priority"] = 2

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400
        )
        chunks = text_splitter.split_documents(pdf_docs)

        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)
        print(f"✅ Successfully embedded {len(chunks)} chunks from '{pdf_path}' into ChromaDB.")
        return len(chunks)
    except Exception as e:
        print(f"❌ Error processing uploaded PDF '{pdf_path}': {e}")
        return 0

def reindex_website_only():
    """
    Re-scrapes all website pages dynamically and updates the ChromaDB vector store.
    Used by the /admin/reindex-website API route in main.py.
    """
    print("🔄 Triggering Admin Website Re-indexing...")
    return process_and_embed_all()

if __name__ == "__main__":
    process_and_embed_all()