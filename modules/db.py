import asyncpg
from typing import Optional, List
import os

class AsyncChatDB:
    def __init__(self):
        self.dsn = os.getenv('PQ_DSN')
        self.pool: asyncpg.pool.Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def close(self):
        if self.pool:
            await self.pool.close()

    # -------- Users --------
    async def create_user(self, username: str, name: str, password_hash: str,
                          profile: Optional[str] = None, bio: Optional[str] = None,
                          status: Optional[str] = None) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO users(username, name, password, profile, bio, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                username, name, password_hash, profile, bio, status
            )
            return result['id']

    async def get_user_by_username(self, username: str) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE username = $1", username)

    async def get_user_by_id(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

    async def login(self, username: str, password_hash: str) -> Optional[int]:
        """
        Returns user id if username + password hash matches, else None.
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT id FROM users WHERE username = $1 AND password = $2",
                username, password_hash
            )
            if result:
                return result['id']
            return None

    async def update_user_profile(self, user_id: int, **kwargs) -> None:
        """
        kwargs can include: name, profile, bio, status, password
        """
        allowed = {"name", "profile", "bio", "status", "password"}
        keys = [k for k in kwargs.keys() if k in allowed]
        if not keys:
            return
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(keys))
        values = [kwargs[k] for k in keys]
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE users SET {sets} WHERE id = $1",
                user_id, *values
            )

    # -------- Chats --------
    async def create_chat(self, chatname: str, chat_title: str, chat_about: str, owner_id: int) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO chats(chatname, chat_title, chat_about, owner)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                chatname, chat_title, chat_about, owner_id
            )
            return result['id']

    async def get_chat_by_name(self, chatname: str) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM chats WHERE chatname = $1", chatname)

    async def get_chat_by_id(self, chatid: int) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM chats WHERE id = $1", chatid)

    async def update_chat_info(self, chat_id: int, **kwargs) -> None:
        """
        kwargs can include: chat_title, chat_about, owner
        """
        allowed = {"chat_title", "chat_about", "owner"}
        keys = [k for k in kwargs.keys() if k in allowed]
        if not keys:
            return
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(keys))
        values = [kwargs[k] for k in keys]
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE chats SET {sets} WHERE id = $1",
                chat_id, *values
            )

    async def remove_group(self, chat_id: int) -> None:
        """
        Deletes chat and cascades due to foreign keys.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM chats WHERE id = $1", chat_id)

    # -------- Chat Rules --------
    async def set_chat_rules(self, user_id: int, chat_id: int,
                             can_ban_user: bool = False, can_remove_message: bool = False,
                             can_send_message: bool = True, can_send_media: bool = True) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_rules(user_id, chat_id, can_ban_user, can_remove_message, can_send_message, can_send_media)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, chat_id) DO UPDATE
                SET can_ban_user = EXCLUDED.can_ban_user,
                    can_remove_message = EXCLUDED.can_remove_message,
                    can_send_message = EXCLUDED.can_send_message,
                    can_send_media = EXCLUDED.can_send_media
                """,
                user_id, chat_id, can_ban_user, can_remove_message, can_send_message, can_send_media
            )

    async def get_chat_rules(self, user_id: int, chat_id: int) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM chat_rules WHERE user_id = $1 AND chat_id = $2",
                user_id, chat_id
            )

    # -------- Dialogs (memberships) --------
    async def join_chat(self, user_id: int, chat_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO dialogs(user_id, chat_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                user_id, chat_id
            )

    async def leave_chat(self, user_id: int, chat_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM dialogs WHERE user_id = $1 AND chat_id = $2
                """,
                user_id, chat_id
            )

    async def get_user_chats(self, user_id: int) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT chats.* FROM chats
                JOIN dialogs ON chats.id = dialogs.chat_id
                WHERE dialogs.user_id = $1
                """,
                user_id
            )
    
    async def is_joined(self, chat_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM dialogs
                    WHERE chat_id = $1 AND user_id = $2
                )
                """,
                chat_id, user_id
            )
            return result


    async def get_chat_users(self, chat_id: int) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT users.* FROM users
                JOIN dialogs ON users.id = dialogs.user_id
                WHERE dialogs.chat_id = $1
                """,
                chat_id
            )
    
    async def send_message(self, chat_id: int, sender_id: int, content: str,
                           reply_to: Optional[int] = None, is_media: bool = False) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO messages(chat_id, sender_id, content, reply_to, is_media)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                chat_id, sender_id, content, reply_to, is_media
            )
            return result["id"]

    async def get_last_messages(self, chat_id: int, offset: int = 0, count: int = 20) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT * FROM messages
                WHERE chat_id = $1
                ORDER BY sent_at DESC
                OFFSET $2 LIMIT $3
                """,
                chat_id, offset, count
            )

    async def delete_message(self, message_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            # Ensure only sender can delete
            result = await conn.execute(
                """
                DELETE FROM messages
                WHERE id = $1 AND sender_id = $2
                """,
                message_id, user_id
            )
            return result.endswith("1")  # e.g., 'DELETE 1'

    async def edit_message(self, message_id: int, user_id: int, new_content: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE messages
                SET content = $1, edited_at = CURRENT_TIMESTAMP
                WHERE id = $2 AND sender_id = $3
                """,
                new_content, message_id, user_id
            )
            return result.endswith("1")