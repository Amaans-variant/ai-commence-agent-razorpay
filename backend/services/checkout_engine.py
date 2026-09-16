import razorpay
from pymongo import MongoClient
from backend.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, MONGO_URI

rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
db_client = MongoClient(MONGO_URI)
db = db_client["ai_commerce"]
products_collection = db["products"]

payment_statuses = {}  # Tracks URL -> Status

def generate_payment_link(product_id: str, proposed_price: int) -> str:
    """Generates a Razorpay link with the negotiated price."""
    product = products_collection.find_one({"id": product_id})
    if not product:
        return None
    
    link_data = {
        "amount": proposed_price,
        "currency": product["currency"],
        "description": product["name"],
        "customer": {"name": "Test Customer", "email": "customer@example.com"},
        "notify": {"email": False, "sms": False},
        "reminder_enable": False
    }
    payment_link = rzp_client.payment_link.create(link_data)
    
    payment_url = payment_link["short_url"]
    url_code = payment_url.split("/")[-1]
    payment_statuses[url_code] = "PENDING"
    
    return payment_url

def update_payment_status(url_code: str, status: str):
    payment_statuses[url_code] = status

def get_payment_status(url_code: str) -> str:
    return payment_statuses.get(url_code, "UNKNOWN")
