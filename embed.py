
import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore_manager import get_vectorstore




def document_load_embed_store(filepath: str) -> str:
    """
    Loads a PDF document from a given file path using the PyMuPDFLoader.
    Splits input documents into smaller chunks, embeds them using a sentence transformer model,
    and stores the resulting vector representations in a persistent Chroma vector database.


    Args:
        filepath (str): The path to the PDF file.

    Returns:
         str: Confirmation message indicating successful storage of embeddings

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file path is not a PDF.
    """
    # Remove quotes if filepath is like "'file.pdf'" or '"file.pdf"'
    print("document_loader tool is called")
    clean_path = filepath.strip('"').strip("'")

    if not os.path.exists(clean_path):
        raise FileNotFoundError(f"File not found: {clean_path}")

    if not clean_path.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported for loading.")

    loader = PyMuPDFLoader(clean_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n"],
    chunk_size=300,
    chunk_overlap=20
        )
    
    chunks = text_splitter.split_documents(documents)
    try:
        vs = get_vectorstore()
        # Delete all existing docs by IDs
        try:
            coll = vs._collection  # chromadb Collection
            all_ids = coll.get()["ids"]  # returns all ids
            if all_ids:
                coll.delete(ids=all_ids)
        except Exception:
            # Fallback: drop the collection if supported, the vectorstore will recreate on next use
            try:
                vs.delete_collection()
            except Exception:
                pass
        vs.add_documents(chunks)
    except Exception as e:
        raise RuntimeError(f"Failed to embed and store documents: {e}")
    
    return "Documents have been embedded and stored in the Chroma vector database."