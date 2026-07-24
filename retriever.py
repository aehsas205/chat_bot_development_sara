from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    try:
        vs = get_vectorstore()
        
        # Fast & lightweight similarity search (k=3 or 4)
        docs = vs.similarity_search(query, k=4)
        
        if not docs:
            print("DEBUG: [Retriever] Zero documents returned!")
            return ""
            
        retrieved_text = "\n\n--- CHUNK ---\n\n".join([doc.page_content for doc in docs])
        print(f"DEBUG: [Retriever] Retrieved {len(docs)} chunks successfully.")
        return retrieved_text
        
    except Exception as e:
        print(f"DEBUG: [Retriever Error] {e}")
        return ""