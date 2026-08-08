"""
AEHSAS Foundation AI Assistant - Vector Store & Embedding Manager
===============================================================
""" 
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ==========================================
# 1. PATH CONFIGURATION & CONSTANTS
# ==========================================
PERSIST_DIR = "./chroma_index"
CHROMA_PATH = "./chroma_index"

# Global Caching Variables
_embeddings_instance = None
_vectorstore_instance = None

def get_vectorstore():
    global _embeddings_instance, _vectorstore_instance

    # 1. Memory Cache Check
    if _vectorstore_instance is not None:
        return _vectorstore_instance

    # 2. Load Model into RAM Once
    if _embeddings_instance is None:
        print("⚡ [Cache] Loading HuggingFace Embeddings into RAM...")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

    # 3. Load Chroma DB Index
    if _vectorstore_instance is None:
        print("⚡ [Cache] Loading ChromaDB Index into RAM...")
        _vectorstore_instance = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=_embeddings_instance
        )

    return _vectorstore_instance