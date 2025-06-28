from fastapi import APIRouter
from models.users import UserLogin, UserRegister
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
    
@router.post('/register')
async def register(user: UserRegister):
    print('here')
    try:
        user_id = await db.create_user(
            user.username,
            user.name,
            hashlib.sha256(user.password.encode('utf-8')).hexdigest()
        )
        return {'status': True, 'user_id': user_id}
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="User Already Exists")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Server side error")


@router.post('/login')
async def post(user: UserLogin):
    try:
        hashed_pw = hashlib.sha256(user.password.encode('utf-8')).hexdigest()
        result = await db.login(user.username, hashed_pw)
        if isinstance(result, int):
            return {'status': True, 'user_id': result}
        raise HTTPException(status_code=403, detail="Wrong username and password combination.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Server side error.")


from fastapi import HTTPException

@router.get('/get')
async def getuser(user_id: int):
    if not user_id:
        raise HTTPException(status_code=400, detail='No user_id.')
    try:
        result = await db.get_user_by_id(user_id)
        if not result:
            raise HTTPException(status_code=404, detail='No user exists with this user_id')

        user_dict = dict(result)
        user_dict['password'] = 'HIDDEN'

        return {'status': True, 'user': user_dict}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Server side error.')

