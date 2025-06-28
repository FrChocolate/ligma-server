from fastapi import APIRouter
from models.users import UserLogin
from modules.db import AsyncChatDB
from models.messages import MessageInput, StreamRequest
from fastapi.responses import StreamingResponse
import hashlib
from fastapi import HTTPException
from fastapi import APIRouter, Request, HTTPException
import uuid
import os
import redis.asyncio as redis
import json

router = APIRouter()
db = AsyncChatDB()

r = redis.Redis()

@router.on_event("startup")
async def startup():
    await db.connect()

@router.post('/get')
async def get_messages(request: UserLogin, chat_id: int=0, chat_name: str=''):
    try:
        if chat_name:
            chat_id_ = await db.get_chat_by_name(chat_name)
            if not chat_id_:
                return HTTPException(404, 'Doesnt exists.')
            chat_id = chat_id_['id']
        messages = await db.get_last_messages(chat_id, 0, 40)
        return {'status_code':200, 'messages':messages}
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')
            

@router.post('/send')
async def send_message(data: MessageInput):
    try:
        # Authenticate user
        password_hash = hashlib.sha256(data.password.encode()).hexdigest()
        user_id = await db.login(data.username, password_hash)
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid username or password.")

        
        chat_id = data.chat_id
        if data.chat_name:
            chat = await db.get_chat_by_name(data.chat_name)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found.")
            chat_id = chat['id']

        
        msg_id = await db.send_message(
            chat_id=chat_id,
            sender_id=user_id,
            content=data.content,
            reply_to=data.reply_to if data.reply_to else None,
            is_media=data.is_media
        )
        await r.publish(f'{chat_id}', json.dumps(dict(chat_id=chat_id,
            sender_id=user_id,
            content=data.content,
            reply_to=data.reply_to if data.reply_to else None,
            is_media=data.is_media)))
        return {'status_code': 200, 'message_id': msg_id}
    except Exception as e:
        print("Error in /send:", e)
        raise HTTPException(status_code=500, detail="Server error.")


@router.post("/upload-media")
async def upload_media(request: Request):
    try:
        body = await request.body()
        if not body:
            raise HTTPException(400, "Empty file body.")

        filename = f"{uuid.uuid4()}.bin"
        filepath = f"static/media/{filename}"

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(body)

        url = f"/media/{filename}"
        return {"status_code": 200, "url": url}
    except Exception as e:
        print("Error uploading media:", e)
        return HTTPException(500, 'Server side error.')

async def wait_for_message(chat_id):
    pubsub = r.pubsub()
    await pubsub.subscribe(f"{chat_id}")
    async for message in pubsub.listen():
        if message['type'] == 'message':
            print(message)
            yield message['data']

@router.post('/stream')
async def streamer(request: StreamRequest):
    try:
        user = await db.login(request.username, hashlib.sha256(request.password.encode('utf-8')).hexdigest())
        if not user:
            return HTTPException(403, 'Unverified session.')
        
        if request.chat_name:
            chat_id = await db.get_chat_by_name(request.chat_name)
            if not chat_id:
                return HTTPException(404, 'Chat does not exists.')
            chat_id = chat_id['id']
        else:
            chat_id = await db.get_chat_by_id(request.chat_id)
            if not chat_id:
                return HTTPException(404, 'Chat does not exists.')
            chat_id = chat_id['id']
        if not await db.is_joined(chat_id, user):
            return HTTPException(403, 'You are not joined in this chat.')

        return StreamingResponse(wait_for_message(chat_id))
    except Exception as e:
        print(e)
        return HTTPException(500, 'Server side error.')