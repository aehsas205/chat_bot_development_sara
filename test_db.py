from vectorstore_manager import get_vectorstore

try:
    print("Testing connection to Supabase...")
    store = get_vectorstore()
    
    # Try adding a test document
    store.add_texts(
        texts=["Connection test successful!"], 
        metadatas=[{"test": True}]
    )
    print("✅ Success! The test data was sent to Supabase.")
    
except Exception as e:
    print("❌ Connection failed!")
    print(f"Error details: {e}")