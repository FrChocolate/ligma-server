from fastapi import FastAPI
from path.users import router as user_router
from modules.db import AsyncChatDB


app = FastAPI()


app.include_router(user_router, prefix='/user')
