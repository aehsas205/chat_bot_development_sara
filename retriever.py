from vectorstore_manager import get_vectorstore

def retrieve_similar_documents(query: str) -> str:
    """
    Robust Universal Retriever.
    Ensures DISHA Career Counselling and all major milestones are fetched.
    """
    try:
        vs = get_vectorstore()
        query_lower = query.lower()
        
         
        docs = vs.similarity_search(query, k=35)
        existing_contents = {d.page_content for d in docs}
        
        
        if any(w in query_lower for w in ["milestone", "milestones", "achievement", "achievements", "program", "events", "disha"]):
            extra = vs.similarity_search(
                "DISHA Career Counselling January 21 2026 AEHSAS Foundation milestones Academic Session Entrance Coaching Free Academic Support Educational Events School Fee Sponsorship Scholarship Spoken English", 
                k=10
            )
            for d in extra:
                if d.page_content not in existing_contents:
                    docs.append(d)
                    existing_contents.add(d.page_content)

        
        if any(w in query_lower for w in ["value", "values","vision", "mission", "motto", "aim"]):
            extra = vs.similarity_search("Vision To build a future-ready inclusive compassionate society education social justice", k=5)
            for d in extra:
                if d.page_content not in existing_contents:
                    docs.append(d)
                    existing_contents.add(d.page_content)
        
        
        if any(w in query_lower for w in ["blog", "blogs", "article", "articles", "mohsin", "faizan", "privilege"]):
            extra = vs.similarity_search(
                "When Privilege Becomes Purpose Why Helping the Underserved Strengthens Everyone Including You Mohd Faizan Co-Founder Secretary 4 min read The Perils of Artificial Intelligence Mohsin Anwer 9 min read", 
                k=10
            )
            for d in extra:
                if d.page_content not in existing_contents:
                    docs.append(d)
                    existing_contents.add(d.page_content)

        if not docs:
            print("DEBUG: [Retriever] Zero documents returned!")
            return ""

        
        docs.sort(key=lambda d: 0 if (d.metadata.get("is_website", False) or str(d.metadata.get("source", "")).startswith("http")) else 1)

        formatted_chunks = []
        for doc in docs:
            source = doc.metadata.get("source", "Knowledge Base")
            is_web = doc.metadata.get("is_website", False) or str(source).startswith("http")
            source_tag = "[SOURCE: LIVE WEBSITE]" if is_web else "[SOURCE: DOCUMENT PDF]"
            formatted_chunks.append(f"{source_tag} [{source}]\n{doc.page_content}")
            
        retrieved_text = "\n\n--- CONTEXT CHUNK ---\n\n".join(formatted_chunks)
        print(f"DEBUG: [Retriever] Total retrieved chunks: {len(docs)}")
        return retrieved_text
        
    except Exception as e:
        print(f"DEBUG: [Retriever Error] {e}")
        return ""

