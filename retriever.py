from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    try:
        vectorstore = get_vectorstore()
        # Direct similarity search on existing index
        docs = vectorstore.similarity_search(query, k=3)
        
        if not docs:
            return "No relevant information found in database."
            
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Error retrieving documents: {str(e)}"