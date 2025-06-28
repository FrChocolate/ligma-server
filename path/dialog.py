from asyncpg.connection import asyncpg
from fastapi import APIRouter
from models.users import UserLogin
from modules.db import AsyncChatDB
from asyncpg.exceptions import UniqueViolationError
import hashlib
import hashlib
from fastapi import HTTPException

router = APIRouter()
db = AsyncChatDB()

@router.on_event("startup")
async def startup():
    await db.connect()

@router.post('/get')
async def dialogs(request: UserLogin):
    try:
        user = await db.login(request.username, request.password_hash)
        if not user:
            return HTTPException(403, 'Unverified session.')
        chats = await db.get_user_chats(user)
        return {'status_code':200, 'chats':chats}
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')

@router.post('/join')
async def join_chat(request: UserLogin, chat_name: str='', chat_id: int=0):
    try:
        if chat_name:
            chat_id_ = await db.get_chat_by_name(chat_name)
            if not chat_id_:
                return HTTPException(404, 'Chat doesnt exists.')
            chat_id = chat_id

        user = await db.login(request.username, request.password_hash)
        if not user:
            return HTTPException(403, 'Unverified session.')
        await db.join_chat(user, chat_id)
        return {'status_code': 200}
    except asyncpg.exceptions.ForeignKeyViolationError:
        return HTTPException(404, 'There is not such a group.')
    except Exception as e:
        return HTTPException(500, 'Server side error.')
