from pydantic import BaseModel
import hashlib


class UserRegister(BaseModel):
    name: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

    @property
    def password_hash(self):
        return hashlib.sha256(self.password.encode('utf-8')).hexdigest()
