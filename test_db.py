from vectorstore_manager import get_vectorstore

try:
    store = get_vectorstore()
    # Database ke saare stored documents check karein
    data = store.get()
    
    docs = data.get("documents", [])
    print("\n================ DATABASE CHECK ================")
    print(f"Total Stored Documents: {len(docs)}")
    
    if len(docs) == 0:
        print("❌ RESULT: Database bilkul KHALI (Empty) hai! Isme PDF ka data nahi hai.")
    else:
        print("✅ RESULT: Data mil gaya! Neeche stored text ka sample dekhein:\n")
        for i, text in enumerate(docs[:3]):
            print(f"--- Document {i+1} ---")
            print(text[:300])  # Pehle 300 characters print karein
            print("-" * 40)
    

except Exception as e:
    print("Error reading ChromaDB:", e)