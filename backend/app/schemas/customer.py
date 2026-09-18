from typing import Literal

from pydantic import BaseModel

Language = Literal["English", "Hindi", "Hinglish"]


class UpdateLanguageRequest(BaseModel):
    preferred_language: Language
