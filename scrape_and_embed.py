import os
import shutil
import glob
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
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

def process_and_embed_all():
    """Reads PDF & Website, chunks text, and embeds into persistent ChromaDB."""
    clear_vectorstore()
    
    documents = []
    
    # 1. Scrape Website
    try:
        print("🌐 Fetching content from website...")
        loader = WebBaseLoader("https://aehsasfoundation.org/")
        web_docs = loader.load()
        documents.extend(web_docs)
        print("✅ Website content extracted!")
    except Exception as e:
        print(f"⚠️ Website scraping error: {e}")

    # 2. Load Local PDF(s)
    pdf_files = glob.glob("*.pdf") + glob.glob("uploads/*.pdf")
    for pdf_path in pdf_files:
        try:
            print(f"📄 Loading PDF: {pdf_path}...")
            loader = PyPDFLoader(pdf_path)
            pdf_docs = loader.load()
            documents.extend(pdf_docs)
            print(f"✅ PDF '{pdf_path}' processed successfully!")
        except Exception as e:
            print(f"⚠️ PDF processing error for {pdf_path}: {e}")

    if not documents:
        print("⚠️ No documents found to embed!")
        return 0

    # 3. Text Chunking (Optimized chunk size & overlap)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(documents)

    # 4. Save to Persistent ChromaDB
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    print(f"✅ Success! Embedded total {len(chunks)} chunks into ChromaDB.")
    return len(chunks)

def process_and_embed_pdf(pdf_path):
    """Processes a single uploaded PDF for Admin Panel without wiping existing DB."""
    try:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
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

# Guard Statement: Runs ONLY when executed manually via terminal
if __name__ == "__main__":
    process_and_embed_all()