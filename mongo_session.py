# ╔══════════════════════════════════════════════════════════════════╗
# ║          AdManager Bot — by @asbhaibsr                          ║
# ║  MongoDB-based Pyrogram Session Storage — Fixed Version          ║
# ║  Koyeb/Heroku/Railway sab pe kaam karta hai — no file needed    ║
# ╚══════════════════════════════════════════════════════════════════╝

import logging
from pymongo import MongoClient
from pyrogram.storage import Storage
from pyrogram.storage.sqlite_storage import get_input_peer

log = logging.getLogger(__name__)


class MongoStorage(Storage):
    """
    Pyrogram session MongoDB mein store karta hai.
    Koyeb restart pe bhi session survive karta hai.
    get_peer_by_id sahi InputPeer object return karta hai — 'tuple has no write' fix.
    """

    USERNAME_TTL = 8 * 60 * 60

    def __init__(self, name: str, mongo_uri: str, db_name: str = "viralbot"):
        super().__init__(name)
        self._mongo_uri = mongo_uri
        self._db_name   = db_name
        self._col       = None
        self._client    = None

        # In-memory cache
        self._dc_id      = 2
        self._api_id     = None
        self._test_mode  = False
        self._auth_key   = None
        self._date       = 0
        self._user_id    = None
        self._is_bot     = True
        self._is_premium = False

    async def open(self):
        self._client = MongoClient(self._mongo_uri)
        col_db  = self._client[self._db_name]
        self._col = col_db[f"pyrogram_session_{self.name}"]
        self._col.create_index("key", unique=True)

        doc = self._col.find_one({"key": "session"})
        if doc:
            self._dc_id      = doc.get("dc_id", 2)
            self._api_id     = doc.get("api_id")
            self._test_mode  = doc.get("test_mode", False)
            self._auth_key   = bytes(doc["auth_key"]) if doc.get("auth_key") else None
            self._date       = doc.get("date", 0)
            self._user_id    = doc.get("user_id")
            self._is_bot     = doc.get("is_bot", True)
            self._is_premium = doc.get("is_premium", False)
            log.info(f"MongoStorage: session loaded uid={self._user_id} dc={self._dc_id}")
        else:
            log.info("MongoStorage: fresh session start")

    async def save(self):
        if self._col is None:
            return
        self._col.update_one(
            {"key": "session"},
            {"$set": {
                "key":        "session",
                "dc_id":      self._dc_id,
                "api_id":     self._api_id,
                "test_mode":  self._test_mode,
                "auth_key":   list(self._auth_key) if self._auth_key else None,
                "date":       self._date,
                "user_id":    self._user_id,
                "is_bot":     self._is_bot,
                "is_premium": self._is_premium,
            }},
            upsert=True
        )

    async def close(self):
        await self.save()
        if self._client:
            self._client.close()

    async def delete(self):
        if self._col:
            self._col.drop()

    async def update_peers(self, peers: list):
        """
        peers = list of (id, access_hash, type, username, phone_number)
        Sab peers store karo — channels, users, groups sab.
        """
        if self._col is None:
            return
        for peer in peers:
            peer_id, access_hash, peer_type, username, phone_number = peer
            self._col.update_one(
                {"key": f"peer_{peer_id}"},
                {"$set": {
                    "key":          f"peer_{peer_id}",
                    "peer_id":      peer_id,
                    "access_hash":  access_hash,
                    "type":         peer_type,
                    "username":     (username or "").lower() if username else None,
                    "phone_number": phone_number,
                }},
                upsert=True
            )
            # Username index bhi update karo
            if username:
                self._col.update_one(
                    {"key": f"username_{username.lower()}"},
                    {"$set": {
                        "key":      f"username_{username.lower()}",
                        "username": username.lower(),
                        "peer_id":  peer_id,
                    }},
                    upsert=True
                )

    async def update_usernames(self, usernames: list):
        """usernames = list of (username, peer_id)"""
        if self._col is None:
            return
        for username, peer_id in usernames:
            if not username:
                continue
            self._col.update_one(
                {"key": f"username_{username.lower()}"},
                {"$set": {
                    "key":      f"username_{username.lower()}",
                    "username": username.lower(),
                    "peer_id":  peer_id,
                }},
                upsert=True
            )

    async def get_peer_by_id(self, peer_id: int):
        """
        CRITICAL FIX: Raw tuple nahi — proper InputPeer object return karo.
        Pehle tuple return karta tha jisse 'tuple has no attribute write' error aata tha.
        """
        if self._col is None:
            raise KeyError(peer_id)
        doc = self._col.find_one({"key": f"peer_{peer_id}"})
        if not doc:
            raise KeyError(peer_id)
        # get_input_peer returns proper InputPeerUser/InputPeerChannel/InputPeerChat
        return get_input_peer(
            doc["peer_id"],
            doc.get("access_hash", 0),
            doc.get("type", "user")
        )

    async def get_peer_by_username(self, username: str):
        if self._col is None:
            raise KeyError(username)
        doc = self._col.find_one({"key": f"username_{username.lower()}"})
        if not doc:
            raise KeyError(username)
        return await self.get_peer_by_id(doc["peer_id"])

    async def get_peer_by_phone_number(self, phone_number: str):
        if self._col is None:
            raise KeyError(phone_number)
        doc = self._col.find_one({
            "phone_number": phone_number,
            "key": {"$regex": "^peer_"}
        })
        if not doc:
            raise KeyError(phone_number)
        return await self.get_peer_by_id(doc["peer_id"])

    # ── Session property accessors ─────────────────────────────────

    async def dc_id(self, value: int = None):
        if value is None:
            return self._dc_id
        self._dc_id = value
        await self.save()

    async def api_id(self, value: int = None):
        if value is None:
            return self._api_id
        self._api_id = value
        await self.save()

    async def test_mode(self, value: bool = None):
        if value is None:
            return self._test_mode
        self._test_mode = value
        await self.save()

    async def auth_key(self, value: bytes = None):
        if value is None:
            return self._auth_key
        self._auth_key = value
        await self.save()

    async def date(self, value: int = None):
        if value is None:
            return self._date
        self._date = value
        await self.save()

    async def user_id(self, value: int = None):
        if value is None:
            return self._user_id
        self._user_id = value
        await self.save()

    async def is_bot(self, value: bool = None):
        if value is None:
            return self._is_bot
        self._is_bot = value
        await self.save()

    async def is_premium(self, value: bool = None):
        if value is None:
            return self._is_premium
        self._is_premium = value
        await self.save()

    async def version(self, value: int = None):
        """Version field — MemoryStorage compatibility ke liye."""
        if value is None:
            return 1
        pass  # version ignore karo
