from fastapi import APIRouter
from models.chats import CreateChat, DeleteChat, JoinChat
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

@router.get('/get')
async def get(chat_id: int=0, chat_name: str=''):
    try:
        if chat_id:
            result = await db.get_chat_by_id(chat_id)
        elif chat_name:
            result = await db.get_chat_by_name(chat_name)
        else:
            return HTTPException(400, 'Wrong usage.')
        if not result:
            return HTTPException(404, 'Not exists.')
        return {'status_code':200, 'chat':dict(result)}
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')

@router.post('/create')
async def create_chat(request: CreateChat):
    try:
        user = await db.login(request.username, hashlib.sha256(request.password.encode('utf-8')).hexdigest())
        if not user:
            return HTTPException(403, 'Unverified session.')
        result = await db.create_chat(request.groupname, request.grouptitle, '', user)
        if not result:
            return HTTPException(409, 'Chat name already exists.')
        await db.join_chat(user, result)
        return {'status_code':200, 'chat_id': result}
    except UniqueViolationError:
        return HTTPException(401, 'Already exists.')
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')

@router.post('/delete')
async def delete_chat(request: DeleteChat):
    try:
        user = await db.login(request.username, hashlib.sha256(request.password.encode('utf-8')).hexdigest())
        if not user:
            return HTTPException(403, 'Unverified session.')
        result = await db.get_chat_by_name(request.groupname)
        if not result:
            return HTTPException(404, 'Group doesnt exists.')
        result = dict(result)
        if result['owner'] == user:
            await db.remove_group(result['id'])
        return {'status':True}
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')


@router.post('/join')
async def join_chat(request: JoinChat):
    try:
        user = await db.login(request.username, hashlib.sha256(request.password.encode('utf-8')).hexdigest())
        if not user:
            return HTTPException(403, 'Unverified session.')
        chat = await db.get_chat_by_name(request.groupname)
        if not chat:
            return HTTPException(404, 'Chat does not exists.')
        await db.join_chat(user, chat['id'])
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')