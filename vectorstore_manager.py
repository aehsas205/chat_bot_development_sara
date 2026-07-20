import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_index")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

