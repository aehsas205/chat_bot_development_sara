import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Embeddings Model (Same used during scraping)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Database Path
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_index")

def get_vectorstore():
    return Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embeddings
    )