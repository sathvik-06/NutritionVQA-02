import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys

async def test():
    print("Testing MongoDB connection...")
    try:
        client = AsyncIOMotorClient(
            'mongodb+srv://nutritionvqa:nutritionvqa123@cluster0.ernjfde.mongodb.net/nutritionvqa?retryWrites=true&w=majority&appName=Cluster0', 
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        await client.admin.command('ping')
        print("SUCCESS: Connected to MongoDB!")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.run(test())
