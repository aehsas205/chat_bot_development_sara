import os
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore

# 1. Configuration
URL = "https://aehsasfoundation.org/"
PDF_PATH = "Chatbot training data.pdf"

def fetch_website_content(url):
    print(f"Fetching content from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching website: Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()

        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return '\n'.join(chunk for chunk in chunks if chunk)
    except Exception as e:
        print(f"Website scraping failed: {e}")
        return None

# Get VectorStore Instance
vectorstore = get_vectorstore()

# Clear Old Database Collection cleanly
try:
    coll = vectorstore._collection
    all_ids = coll.get()["ids"]
    if all_ids:
        coll.delete(ids=all_ids)
        print("🧹 Old database cleared successfully!")
except Exception as e:
    print(f"Database clear note: {e}")

all_chunks = []

# --- PART 1: WEBSITE CONTENT ---
clean_text = fetch_website_content(URL)
if clean_text:
    print("🌐 Website content extracted!")
    doc = Document(page_content=clean_text, metadata={"source": URL})
    # Optimized chunk size to preserve full paragraphs
    web_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_chunks.extend(web_splitter.split_documents([doc]))

# --- PART 2: PDF CONTENT ---
if os.path.exists(PDF_PATH):
    print(f"📄 Loading PDF: {PDF_PATH}...")
    pdf_loader = PyMuPDFLoader(PDF_PATH)
    pdf_docs = pdf_loader.load()
    
    # Larger chunk_size ensures full membership definitions stay in a single chunk
    # RecursiveCharacterTextSplitter update karein
    pdf_splitter = RecursiveCharacterTextSplitter( chunk_size=1500, chunk_overlap=300, separators=["\n\n", "\n", " ", ""])
    all_chunks.extend(pdf_splitter.split_documents(pdf_docs))
    print("📄 PDF content processed with optimal chunks!")
else:
    print(f"⚠️ Warning: PDF file '{PDF_PATH}' not found!")

# --- PART 3: EMBED EVERYTHING TO CHROMADB ---
if all_chunks:
    print(f"Embedding total {len(all_chunks)} chunks (Website + PDF) into ChromaDB...")
    vectorstore.add_documents(all_chunks)
    print("✅ Success! Both Website and PDF content are now stored with full context in ChromaDB.")
else:
    print("❌ No content found to embed.")





def process_and_embed_pdf(pdf_file_path: str):
    """
    Processes a single uploaded PDF file and appends its embeddings to ChromaDB.
    """
    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"PDF file not found at path: {pdf_file_path}")

    print(f"📄 Processing newly uploaded PDF: {pdf_file_path}...")
    
    # Load PDF
    pdf_loader = PyMuPDFLoader(pdf_file_path)
    pdf_docs = pdf_loader.load()

    if not pdf_docs:
        raise ValueError("The uploaded PDF is empty or could not be read.")

    # Split into chunks (same optimal chunk size)
    pdf_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        separators=["\n\n", "\n", " ", ""]
    )
    pdf_chunks = pdf_splitter.split_documents(pdf_docs)

    # Embed & Add to ChromaDB
    vs = get_vectorstore()
    vs.add_documents(pdf_chunks)
    
    print(f"✅ Successfully embedded {len(pdf_chunks)} chunks from '{os.path.basename(pdf_file_path)}' into ChromaDB!")
    return len(pdf_chunks)





#----------------------------------------------#
# update any changes in website
#----------------------------------------------#
def reindex_website_only():
    """Fetches latest website content and updates ChromaDB embeddings."""
    print("🌐 Re-indexing website content...")
    clean_text = fetch_website_content(URL)
    if clean_text:
        doc = Document(page_content=clean_text, metadata={"source": URL})
        web_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        web_chunks = web_splitter.split_documents([doc])
        
        vs = get_vectorstore()
        vs.add_documents(web_chunks)
        print(f"✅ Re-indexed {len(web_chunks)} website chunks into ChromaDB!")
        return len(web_chunks)
    return 0