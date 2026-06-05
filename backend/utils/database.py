import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from config.settings import settings

logger = logging.getLogger("database")

# Global clients
_async_client = None
_async_db = None
_sync_client = None
_sync_db = None

async def get_async_db():
    """Get or create the async MongoDB client and database."""
    global _async_client, _async_db
    if _async_db is None:
        try:
            logger.info("Initializing async MongoDB client...")
            # Add 5 second timeout to prevent infinite hang if DB is down
            _async_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
            _async_db = _async_client[settings.MONGODB_DB_NAME]
            # Check connection
            await _async_client.admin.command('ping')
            logger.info("Async MongoDB connected successfully.")
        except Exception as e:
            logger.error(f"⚠️ MongoDB connection failed (features limited): {e}")
            # Do NOT raise error, keep server online
            _async_db = None
    return _async_db

async def close_async_db():
    """Close the async MongoDB client."""
    global _async_client
    if _async_client:
        _async_client.close()
        logger.info("Async MongoDB client closed.")

def get_sync_db():
    """Get or create the synchronous MongoDB client and database."""
    global _sync_client, _sync_db
    if _sync_db is None:
        try:
            logger.info("Initializing sync MongoDB client...")
            _sync_client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
            )
            _sync_db = _sync_client[settings.MONGODB_DB_NAME]
            # Check connection
            _sync_client.admin.command('ping')
            logger.info("Sync MongoDB connected successfully.")
        except Exception as e:
            logger.error(f"⚠️ Sync MongoDB connection failed: {e}")
            # Do NOT raise error, keep server online
            _sync_db = None
    return _sync_db

def close_sync_db():
    """Close the synchronous MongoDB client."""
    global _sync_client
    if _sync_client:
        _sync_client.close()
        logger.info("Sync MongoDB client closed.")

