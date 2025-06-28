from pydantic import BaseModel

class CreateChat(BaseModel):
    username: str
    password: str
    groupname: str
    groupname: str
    grouptitle: str

class DeleteChat(BaseModel):
    username: str
    password: str
    groupname: str

class JoinChat(BaseModel):
    username: str
    password: str
    groupname: str