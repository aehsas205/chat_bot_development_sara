import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

CHROMA_PATH = "./chroma_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def get_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Ensure directory exists on server
    os.makedirs(CHROMA_PATH, exist_ok=True)
    
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    return vectorstore