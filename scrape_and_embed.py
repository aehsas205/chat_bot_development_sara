import os
import shutil
import glob
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore, CHROMA_PATH

def clear_vectorstore():
    """Wipes the existing Chroma database if explicitly called."""
    if os.path.exists(CHROMA_PATH):
        try:
            shutil.rmtree(CHROMA_PATH)
            print("🧹 Old database cleared successfully!")
        except Exception as e:
            print(f"⚠️ Warning clearing vectorstore: {e}")

def get_website_urls():
    """List of all essential website pages including team and post incumbents."""
    base_url = "https://aehsasfoundation.org"
    return [
        f"{base_url}/",
        f"{base_url}/about",
        f"{base_url}/about-us",
        f"{base_url}/our-team",
        f"{base_url}/team",
        f"{base_url}/leadership",
        f"{base_url}/patrons",
        f"{base_url}/founding-members",
        f"{base_url}/post-incumbents",
        f"{base_url}/former-incumbents",
        f"{base_url}/testimonials",
        f"{base_url}/contact",
        f"{base_url}/contact-us",
        f"{base_url}/our-work",
        f"{base_url}/our-contributions",
        f"{base_url}/milestones",
        f"{base_url}/donate",
        f"{base_url}/memberships",
        f"{base_url}/membership",
        f"{base_url}/join-us",
        f"{base_url}/blog"
    ]

def fetch_unfiltered_web_document(url: str) -> Document:
    """Fetches raw webpage text without truncating any team grid or list nodes."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    raw_lines = soup.get_text(separator="\n").splitlines()
    cleaned_lines = [line.strip() for line in raw_lines if line.strip()]
    full_text = "\n".join(cleaned_lines)
    
    return Document(
        page_content=full_text,
        metadata={"source": url}
    )

def process_and_embed_all():
    """Scrapes websites and PDFs with chunk_size=1500 to keep full rosters together."""
    clear_vectorstore()
    documents = []
    
    urls = get_website_urls()
    print(f"🌐 Fetching raw content from {len(urls)} website URLs...")
    
    for url in urls:
        try:
            doc = fetch_unfiltered_web_document(url)
            if doc.page_content:
                documents.append(doc)
                print(f"  ✅ Extracted full text from: {url}")
        except Exception as e:
            print(f"  ⚠️ Note on {url}: {e}")

    # Process PDFs
    pdf_files = glob.glob("*.pdf") + glob.glob("uploads/*.pdf")
    for pdf_path in pdf_files:
        try:
            print(f"📄 Loading PDF: {pdf_path}...")
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            for p_doc in pdf_docs:
                p_doc.metadata["source"] = pdf_path
            documents.extend(pdf_docs)
            print(f"✅ PDF '{pdf_path}' processed successfully!")
        except Exception as e:
            print(f"⚠️ PDF processing error for {pdf_path}: {e}")

    if not documents:
        print("⚠️ No documents found to embed!")
        return 0

    # chunk_size=1500 prevents team lists from being sliced into multiple chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300
    )
    chunks = text_splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    print(f"✅ Success! Embedded total {len(chunks)} chunks into ChromaDB.")
    return len(chunks)

def process_and_embed_pdf(pdf_path):
    """Processes a single uploaded PDF."""
    try:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
        chunks = text_splitter.split_documents(docs)
        
        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)
        return len(chunks)
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        raise e

def reindex_website_only():
    """Re-indexes website content."""
    return process_and_embed_all()

if __name__ == "__main__":
    process_and_embed_all()