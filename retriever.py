from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    """
    Retrieves relevant chunks from ChromaDB.
    Automatically prioritizes Live Website documents over PDF files whenever available
    to prevent stale document conflicts.
    """
    try:
        vs = get_vectorstore()
        
        # Initial search query
        docs = vs.similarity_search(query, k=15)
        
        query_lower = query.lower()
        team_keywords = [
            "post", "holder", "team", "leader", "executive", "office", 
            "bearer", "member", "founder", "founding", "roster", "incumbent", 
            "director", "coordinator", "manager", "former", "patron"
        ]
        
        if any(term in query_lower for term in team_keywords):
            # Broaden search for leadership and roster pages
            expanded_query = "AEHSAS Foundation Our Current Post Holders Founding Members Former Incumbents leadership team roster"
            extra_docs = vs.similarity_search(expanded_query, k=15)
            
            existing_contents = {d.page_content for d in docs}
            for d in extra_docs:
                if d.page_content not in existing_contents:
                    docs.append(d)
                    existing_contents.add(d.page_content)
        
        if not docs:
            print("DEBUG: [Retriever] Zero documents returned!")
            return ""

        def get_doc_priority(doc):
            is_website = doc.metadata.get("is_website", False)
            source = str(doc.metadata.get("source", ""))
            if is_website or source.startswith("http"):
                return 0  # Highest priority
            return 1      # Secondary priority (PDFs/Files)

        docs.sort(key=get_doc_priority)
            
        formatted_chunks = []
        for doc in docs:
            source = doc.metadata.get("source", "Knowledge Base")
            title = doc.metadata.get("title", "")
            is_web = doc.metadata.get("is_website", False) or source.startswith("http")
            
            source_tag = "[SOURCE: LIVE WEBSITE]" if is_web else "[SOURCE: DOCUMENT PDF]"
            meta_str = f"{source_tag} [URL/File: {source}]"
            if title:
                meta_str += f" [Title: {title}]"
                
            formatted_chunks.append(f"{meta_str}\n{doc.page_content}")
            
        retrieved_text = "\n\n--- CONTEXT CHUNK ---\n\n".join(formatted_chunks)
        print(f"DEBUG: [Retriever] Retrieved {len(docs)} total relevant chunks (Website prioritized).")
        return retrieved_text
        
    except Exception as e:
        print(f"DEBUG: [Retriever Error] {e}")
        return ""