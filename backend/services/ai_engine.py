from google import genai
from google.genai import types
import json
from backend.config import GEMINI_API_KEY
from backend.models.schemas import AgentResponse
from backend.services.checkout_engine import products_collection

ai_client = genai.Client(api_key=GEMINI_API_KEY)
active_chats = {}

def get_chat_session(session_id: str):
    if session_id not in active_chats:
        catalog_list = list(products_collection.find({}, {"_id": 0}))
        
        system_instruction = f"""
        You are an expert AI sales orchestrator and sales negotiator. Here is your catalog:
        {json.dumps(catalog_list)}
        
        Rules:
        1. Answer questions clearly and summarize product benefits.
        2. THE UPSELL: When a user asks about a single product, proactively suggest the second product as a complementary bundle. Explain why they work well together.
        3. You are a sales negotiator. You can offer slight discounts to close a deal, but you must ask the user for their offer first.
        4. You must set the intent to 'checkout' when an agreement on price is reached and the user wants to buy. Ensure product_id and proposed_price are populated correctly.
        5. You must set the 'action' field to one of ["NONE", "SHOW_PRODUCT", "SHOW_CART", "NEGOTIATE"]. Set to 'SHOW_PRODUCT' when discussing a specific product.
        """
        
        active_chats[session_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AgentResponse,
                temperature=0.3
            )
        )
    return active_chats[session_id]
