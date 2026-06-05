import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient('mongodb+srv://nutritionvqa:nutritionvqa123@cluster0.ernjfde.mongodb.net/nutritionvqa?retryWrites=true&w=majority&appName=Cluster0')
    db = client['nutritionvqa']
    user = await db.users.find_one({'email': 'sathvikch2006@gmail.com'})
    print("Mobile:", user['mobile'] if user else 'User not found')

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
