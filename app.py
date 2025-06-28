from fastapi import FastAPI
from path import messages
from path.users import router as user_router
from path.chats import router as chat_router
from path.dialog import router as dialog_router
from path.messages import router as messages_router

app = FastAPI()


app.include_router(user_router, prefix='/user')
app.include_router(chat_router, prefix='/chat')
app.include_router(dialog_router, prefix='/dialog')
app.include_router(messages_router, prefix='/messages')
