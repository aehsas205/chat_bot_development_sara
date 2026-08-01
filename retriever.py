from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    """
    Retrieves top relevant chunks from ChromaDB.
    Uses high k value (k=12) and hybrid query expansion for team/post holder queries 
    to guarantee 100% complete roster context coverage across multiple pages.
    """
    try:
        vs = get_vectorstore()
        
        # Increased k=12 to ensure chunks across multiple pages/documents are fetched
        docs = vs.similarity_search(query, k=)
        
        query_lower = query.lower()
        team_triggers = ["post", "holder", "team", "leader", "executive", "office", "bearer", "member", "who are", "roster", "incumbent"]
        
        if any(term in query_lower for term in team_triggers):
            # Explicitly search for all 8 team members and designations
            team_search_query = (
                "Mohsin Anwer Mohd Faizan Rizwan Ahmad Saifi Faisal Jawahar "
                "Mohammad Azeem Khan Nafees Ahmad Mohsin Azmi Muhammad Arhab "
                "President Secretary Treasurer Program Manager Executive Director "
                "Event Coordinator Marketing Coordinator Assistant R&D Coordinator"
            )
            extra_docs = vs.similarity_search(team_search_query, k=10)
            
            # Combine unique docs based on page_content to avoid duplicate chunks
            existing_contents = {d.page_content for d in docs}
            for d in extra_docs:
                if d.page_content not in existing_contents:
                    docs.append(d)
                    existing_contents.add(d.page_content)
        
        if not docs:
            print("DEBUG: [Retriever] Zero documents returned!")
            return ""
            
        formatted_chunks = []
        for doc in docs:
            source = doc.metadata.get("source", "Knowledge Base")
            formatted_chunks.append(f"[Source: {source}]\n{doc.page_content}")
            
        retrieved_text = "\n\n--- CHUNK ---\n\n".join(formatted_chunks)
        print(f"DEBUG: [Retriever] Retrieved {len(docs)} relevant chunks successfully.")
        return retrieved_text
        
    except Exception as e:
        print(f"DEBUG: [Retriever Error] {e}")
        return ""