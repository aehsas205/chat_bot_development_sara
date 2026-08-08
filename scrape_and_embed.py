import os
import shutil
import glob
import time
import requests
from urllib.parse import urlparse, urljoin
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

def discover_all_website_urls(base_url: str = "https://aehsasfoundation.org") -> list:
    """
    Automatically crawls internal links up to 2 levels deep across the website.
    Discovers new blogs, privacy policy, careers, terms, and custom sub-pages without manual entry.
    """
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
                print(f"  ⚠️ Crawler notice fetching links from {url}: {e}")

    fallback_urls = [
        f"{base_url}/",
        f"{base_url}/about",
        f"{base_url}/about-us",
        f"{base_url}/our-team",
        f"{base_url}/founding-members",
        f"{base_url}/post-incumbents",
        f"{base_url}/former-incumbents",
        f"{base_url}/patrons",
        f"{base_url}/contact",
        f"{base_url}/our-work",
        f"{base_url}/milestones",
        f"{base_url}/donate",
        f"{base_url}/membership",
        f"{base_url}/press-releases",
        f"{base_url}/careers",
        f"{base_url}/privacy-policy",
        f"{base_url}/license",
        f"{base_url}/tc",
        f"{base_url}/blog",
        f"{base_url}/blog/1",
        f"{base_url}/blog/2",
        f"{base_url}/blog/3"
    ]
    for fallback in fallback_urls:
        to_visit.add(fallback.rstrip("/"))

    final_url_list = list(to_visit)
    print(f"🌐 Auto-Discovered {len(final_url_list)} unique internal website pages to scrape.")
    return final_url_list

def fetch_web_document_dynamic(url: str) -> Document:
    """
    Fetches text content from dynamic React SPAs using Selenium Headless Chrome.
    Extracts complete DOM tree (including hidden carousel slides like testimonials)
    by combining Selenium DOM evaluation with BeautifulSoup page source parsing.
    """
    full_text = ""
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(3)
        

        
        driver.execute_script("""
            let totalHeight = 0;
            let distance = 300;
            let timer = setInterval(() => {
                let scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeight) {
                    clearInterval(timer);
                }
            }, 100);
        """)
        time.sleep(3)
        
        
        driver.execute_script("""
            let nextBtns = document.querySelectorAll('.slick-next, .swiper-button-next, button[aria-label*="next"], .carousel-control-next');
            nextBtns.forEach(btn => {
                for(let i=0; i<5; i++) {
                    try { btn.click(); } catch(e) {}
                }
            });
        """)
        time.sleep(1)

        rendered_text = driver.execute_script("return document.body.innerText;")
        
        
        hydrated_soup = BeautifulSoup(driver.page_source, "html.parser")
        for element in hydrated_soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        dom_text = hydrated_soup.get_text(separator="\n")
        
        page_title = driver.title or url
        driver.quit()

        combined_lines = []
        seen_lines = set()

        for raw_line in (rendered_text + "\n" + dom_text).splitlines():
            line = raw_line.strip()
            if line and "JavaScript" not in line and line not in seen_lines:
                seen_lines.add(line)
                combined_lines.append(line)

        full_text = f"Live Website Content Page: {page_title} ({url})\n" + "\n".join(combined_lines)

    except Exception as e:
        print(f"  ⚠️ Selenium fetch failed for {url} ({e}), falling back to requests...")
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

def process_and_embed_all():
    """
    Clears existing vector DB, automatically crawls and scrapes all website URLs,
    processes local PDF files, and embeds large structured chunks (5000 chars) into ChromaDB
    to avoid splitting core values, testimonials, or team rosters across chunk boundaries.
    """
    clear_vectorstore()
    documents = []
    
    urls = discover_all_website_urls()
    print(f"🌐 Fetching live website pages ({len(urls)} URLs)...")
    for url in urls:
        try:
            doc = fetch_web_document_dynamic(url)
            if len(doc.page_content) > 80:
                documents.append(doc)
                print(f"  ✅ Dynamically Scraped Website Page: {url}")
        except Exception as e:
            print(f"  ⚠️ Skipping {url}: {e}")

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

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=600
    )
    chunks = text_splitter.split_documents(documents)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    print(f"🎉 Success! Embedded total {len(chunks)} chunks into ChromaDB.")
    return len(chunks)

def process_and_embed_pdf(pdf_path: str):
    """Processes a single newly uploaded PDF file."""
    try:
        print(f"📄 Processing newly uploaded PDF: {pdf_path}...")
        loader = PyPDFLoader(pdf_path)
        pdf_docs = loader.load()
        for p_doc in pdf_docs:
            p_doc.metadata["source"] = pdf_path
            p_doc.metadata["is_website"] = False
            p_doc.metadata["priority"] = 2

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=500
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
    """Re-scrapes all website pages dynamically and updates ChromaDB."""
    print("🔄 Triggering Admin Website Re-indexing...")
    return process_and_embed_all()

if __name__ == "__main__":
    process_and_embed_all()