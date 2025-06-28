from pydantic import BaseModel
from typing import Optional

class MessageInput(BaseModel):
    username: str
    password: str
    content: str
    chat_id: Optional[int] = 0
    chat_name: Optional[str] = ''
    reply_to: Optional[int] = None
    is_media: Optional[bool] = False

class StreamRequest(BaseModel):
    username: str
    password: str
    chat_id: int = 0
    chat_name: str = ''