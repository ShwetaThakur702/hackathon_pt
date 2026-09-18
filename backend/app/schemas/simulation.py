from pydantic import BaseModel


class AdvanceTimeRequest(BaseModel):
    days: int = 0
    hours: int = 0
