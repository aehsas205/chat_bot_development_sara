import os
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore

# 1. Website URL
URL = "https://aehsasfoundation.org/"

def fetch_website_content(url):
    print(f"Fetching content from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching website: Status {response.status_code}")
        return None

    # HTML parsing with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Unnecessary elements cleaning (scripts, styles, nav etc.)
    for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
        script_or_style.decompose()

    # Text Extraction
    text = soup.get_text(separator=' ')
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return clean_text

# 2. Main Logic
clean_text = fetch_website_content(URL)

if clean_text:
    print("Content successfully extracted!")
    
    # LangChain Document Object
    doc = Document(page_content=clean_text, metadata={"source": URL})

    # Text Chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents([doc])

    # Save to ChromaDB
    print("Embedding website content into ChromaDB...")
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    print("✅ Success! Website content is stored in ChromaDB.")