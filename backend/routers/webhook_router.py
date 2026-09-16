import json
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Request
from backend.config import RAZORPAY_WEBHOOK_SECRET
from backend.services.checkout_engine import update_payment_status, get_payment_status

router = APIRouter()

@router.post("/webhook")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    try:
        expected_signature = hmac.new(
            bytes(RAZORPAY_WEBHOOK_SECRET, 'latin-1'),
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
        
        url_code = paid_url.split("/")[-1]
        update_payment_status(url_code, "PAID")
        print(f"✅ SUCCESS! Payment Link {order_id} was paid!")
        
    elif event_type == "payment_link.cancelled":
        print("❌ Payment Link was cancelled or expired.")

    return {"status": "ok"}

@router.get("/status")
def check_payment_status(url: str):
    url_code = url.split("/")[-1]
    return {"status": get_payment_status(url_code)}
