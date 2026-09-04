from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# 2. Global dictionary to hold active conversations (Memory)
active_chats = {}

payment_statuses = {}  # Tracks URL -> Status

def generate_payment_link(product_id: str) -> str:
    """Tool for the AI to call when the user agrees to purchase an item."""
    
    # NEW MONGODB METHOD: Search for the product ID in the database
    product = products_collection.find_one({"id": product_id})
    
    if not product:
        return "Product not found."
    
    link_data = {
        "amount": product["price_in_paise"],
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
    You are an expert AI sales orchestrator. Here is your catalog:
    {json.dumps(catalog_list)}
    
    Rules:
    1. Answer questions clearly and summarize product benefits.
    2. THE UPSELL: When a user asks about a single product, proactively suggest the second product as a complementary bundle. Explain why they work well together.
    3. When the user confirms they want to buy, call the `generate_payment_link` tool.
    4. Return the payment link directly to the user once generated.
    """
    
    # Initialize a new chat memory if this user doesn't have one yet
    if req.session_id not in active_chats:
        active_chats[req.session_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[generate_payment_link],
                temperature=0.3
            )
        )
    
    # Retrieve the active chat session from memory
    chat = active_chats[req.session_id]
    
    try:
        # Send the message to the memory-aware chat object
        response = chat.send_message(req.message)
        return {"reply": response.text}
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