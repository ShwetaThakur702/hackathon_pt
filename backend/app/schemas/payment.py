from typing import Literal

from pydantic import BaseModel


class SendPaymentRequest(BaseModel):
    customer_id: str
    recipient_name: str
    recipient_type: Literal["CONTACT", "MERCHANT"] = "CONTACT"
    amount: float
