import os
from dotenv import load_dotenv # 1. Add this import
from supabase import create_client, Client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

# 2. Add this line to load your .env file
load_dotenv() 

# Now these will successfully read from your .env file
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  

TABLE_NAME = "chatbot_history"  
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# ... (keep the rest of your file exactly the same)

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

vectorstore = None

def get_vectorstore():
    global vectorstore
    if vectorstore is None:
        # Initialize the Supabase client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Initialize the LangChain Supabase vector store wrapper
        vectorstore = SupabaseVectorStore(
            client=supabase_client,
            embedding=embeddings,
            table_name=TABLE_NAME,
            query_name="match_documents",  # The matching function defined in Supabase
        )
    return vectorstore