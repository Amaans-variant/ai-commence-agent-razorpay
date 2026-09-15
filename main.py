from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import razorpay
import os
import hmac
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pymongo import MongoClient

# Load the secrets from the .env file
load_dotenv()

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Securely fetch your keys
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Initialize Clients
rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize MongoDB Connection
db_client = MongoClient(MONGO_URI)
db = db_client["ai_commerce"]
products_collection = db["products"]

# 1. Update request to expect a session ID
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

class AgentResponse(BaseModel):
    message: str
    intent: str
    product_id: Optional[str] = None
    proposed_price: Optional[int] = None

# 2. Global dictionary to hold active conversations (Memory)
active_chats = {}

payment_statuses = {}  # Tracks URL -> Status

def generate_payment_link(product_id: str, proposed_price: int) -> str:
    """Generates a Razorpay link with the negotiated price."""
    
    # NEW MONGODB METHOD: Search for the product ID in the database
    product = products_collection.find_one({"id": product_id})
    
    if not product:
        return "Product not found."
    
    link_data = {
        "amount": proposed_price,
        "currency": product["currency"],
        "description": product["name"],
        "customer": {"name": "Test Customer", "email": "customer@example.com"},
        "notify": {"email": False, "sms": False},
        "reminder_enable": False
    }
    payment_link = rzp_client.payment_link.create(link_data)
    
    # Save the initial status using just the unique code at the end
    payment_url = payment_link["short_url"]
    url_code = payment_url.split("/")[-1]
    payment_statuses[url_code] = "PENDING"
    
    return payment_url

@app.post("/chat")
def chat_with_agent(req: ChatRequest):

    # Fetch all products from MongoDB to give to the AI, excluding the internal MongoDB '_id' field
    catalog_list = list(products_collection.find({}, {"_id": 0}))

    system_instruction = f"""
    You are an expert AI sales orchestrator and sales negotiator. Here is your catalog:
    {json.dumps(catalog_list)}
    
    Rules:
    1. Answer questions clearly and summarize product benefits.
    2. THE UPSELL: When a user asks about a single product, proactively suggest the second product as a complementary bundle. Explain why they work well together.
    3. You are a sales negotiator. You can offer slight discounts to close a deal, but you must ask the user for their offer first.
    4. You must set the intent to 'checkout' when an agreement on price is reached and the user wants to buy. Ensure product_id and proposed_price are populated correctly.
    """
    
    # Initialize a new chat memory if this user doesn't have one yet
    if req.session_id not in active_chats:
        active_chats[req.session_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AgentResponse,
                temperature=0.3
            )
        )
    
    # Retrieve the active chat session from memory
    chat = active_chats[req.session_id]
    
    try:
        # Send the message to the memory-aware chat object
        response = chat.send_message(req.message)
        response_text = response.text
        
        try:
            json_resp = json.loads(response_text)
        except json.JSONDecodeError:
            return {"reply": response_text}
            
        message = json_resp.get("message", "")
        intent = json_resp.get("intent", "")
        product_id = json_resp.get("product_id")
        proposed_price = json_resp.get("proposed_price")

        if intent == "checkout" and product_id and proposed_price:
            product = products_collection.find_one({"id": product_id})
            if product:
                floor_price = product.get("floor_price", 0)
                if proposed_price >= floor_price:
                    payment_link = generate_payment_link(product_id, proposed_price)
                    message += f"\n\nHere is your payment link: {payment_link}"
                else:
                    # SYSTEM OVERRIDE
                    system_override_msg = f"SYSTEM: The proposed price of {proposed_price} is below the floor limit. Apologize to the user and counter-offer with a price higher than {floor_price}."
                    new_response = chat.send_message(system_override_msg)
                    try:
                        new_json = json.loads(new_response.text)
                        message = new_json.get("message", "")
                    except:
                        message = new_response.text

        return {"reply": message}
    except Exception as e:
        return {"reply": f"An error occurred: {str(e)}"}

@app.post("/webhook")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    try:
        expected_signature = hmac.new(
            bytes(secret, 'latin-1'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        if expected_signature != signature:
            raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Signature verification failed")

    event_data = json.loads(payload)
    event_type = event_data.get("event")

    if event_type == "payment_link.paid":
        order_id = event_data["payload"]["payment_link"]["entity"]["id"]
        paid_url = event_data["payload"]["payment_link"]["entity"]["short_url"]
        
        # Mark the unique code as PAID
        url_code = paid_url.split("/")[-1]
        payment_statuses[url_code] = "PAID"
        
        print(f"✅ SUCCESS! Payment Link {order_id} was paid!")
        
    elif event_type == "payment_link.cancelled":
        print("❌ Payment Link was cancelled or expired.")

    return {"status": "ok"}

@app.get("/status")
def check_payment_status(url: str):
    url_code = url.split("/")[-1]
    return {"status": payment_statuses.get(url_code, "UNKNOWN")}