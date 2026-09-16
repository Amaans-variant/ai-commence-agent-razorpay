from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

class AgentResponse(BaseModel):
    message: str
    intent: str
    action: str
    product_id: Optional[str] = None
    proposed_price: Optional[int] = None
