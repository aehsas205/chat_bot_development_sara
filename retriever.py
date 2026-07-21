from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    try:
        vs = get_vectorstore()
        
        # Search using MMR to ensure diverse & high-relevant context retrieval
        docs = vs.max_marginal_relevance_search(query, k=8, fetch_k=20)
        
        if not docs:
            print("DEBUG: [Retriever] Zero documents returned!")
            return ""
            
        retrieved_text = "\n\n--- CHUNK ---\n\n".join([doc.page_content for doc in docs])
        print(f"DEBUG: [Retriever] Retrieved {len(docs)} chunks successfully.")
        return retrieved_text
        
    except Exception as e:
        print(f"DEBUG: [Retriever Error] {e}")
        return ""