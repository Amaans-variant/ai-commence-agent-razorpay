import json
from fastapi import APIRouter
from backend.models.schemas import ChatRequest
from backend.services.ai_engine import get_chat_session
from backend.services.checkout_engine import products_collection, generate_payment_link

router = APIRouter()

@router.post("/chat")
def chat_with_agent(req: ChatRequest):
    chat = get_chat_session(req.session_id)
    
    try:
        response = chat.send_message(req.message)
        response_text = response.text
        
        try:
            json_resp = json.loads(response_text)
        except json.JSONDecodeError:
            return {"message": response_text, "action": "NONE", "data": None}
            
        message = json_resp.get("message", "")
        intent = json_resp.get("intent", "")
        action = json_resp.get("action", "NONE")
        product_id = json_resp.get("product_id")
        proposed_price = json_resp.get("proposed_price")
        
        data = None
        payment_link = None

        if product_id:
            product = products_collection.find_one({"id": product_id}, {"_id": 0})
            if product:
                data = product

        if intent == "checkout" and product_id and proposed_price:
            if data:
                floor_price = data.get("floor_price", 0)
                if proposed_price >= floor_price:
                    payment_link = generate_payment_link(product_id, proposed_price)
                else:
                    system_override_msg = f"SYSTEM: The proposed price of {proposed_price} is below the floor limit. Apologize to the user and counter-offer with a price higher than {floor_price}."
                    new_response = chat.send_message(system_override_msg)
                    try:
                        new_json = json.loads(new_response.text)
                        message = new_json.get("message", "")
                        action = new_json.get("action", action)
                    except:
                        message = new_response.text

        return {
            "message": message,
            "action": action,
            "data": data,
            "payment_link": payment_link
        }
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}", "action": "NONE", "data": None}
