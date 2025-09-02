from typing import List
from langchain_core.tools import tool
from vectorstore_manager import get_vectorstore
import time
import logging

logger = logging.getLogger("aehsas")

@tool
def retrieve_similar_documents(query: str) -> List[str]:
    """
    Loads a persisted Chroma vector database from disk and performs a similarity search
    based on a natural language query.
    """
    logger.info("retrieve_similar_documents called: %s", query)
    t0=time.time()
    vs=get_vectorstore()
    t1=time.time()
    
    results = vs.similarity_search(query, k=3)

    t2=time.time()
    logger.debug("[RAG] open=%.3fs search=%.3fs", (t1 - t0), (t2 - t1))
    l=[doc.page_content for doc in results]
    s=""
    for i in l:
        i.replace("\n\uf0b7","")
        s=s+i
    return s


