from supabase import Client, create_client
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

load_dotenv()

# CONEXÂO COM SUPABASE
supabase_url = os.getenv("PROJECT_URL_SUPABASE")
supabase_key = os.getenv("API_KEY_SUPABASE")
supabase: Client = create_client(supabase_url, supabase_key)

# CONEXÃO COM EVOLUTION
base_url_evo = os.getenv("BASE_URL_EVO")
instance_token = os.getenv("API_KEY_EVO") 
url = f"{base_url_evo}/message/sendText/agentei_ia"
headers = {
    "Content-Type": "application/json",
    "apikey": instance_token
}

# CONEXÃO COM A GROQ 
llm_groq = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-70b-8192", temperature=0.2)