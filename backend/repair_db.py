import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def repair_database():
    print("🛠️ Starting Database Repair...")
    try:
        # Use the URI from your settings (local for now)
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client['nutritionvqa']
        
        # 1. Update users who have missing or "N/A" mobile numbers to a placeholder.
        # We do not overwrite users who already have a valid mobile number.
        result = await db.users.update_many(
            {"$or": [{"mobile": {"$exists": False}}, {"mobile": "N/A"}]}, 
            {"$set": {"mobile": "0000000000"}}
        )
        
        print(f"✅ Success! Updated {result.modified_count} users to use mobile number: 0000000000")
        
        # 2. Verify it happened
        users = await db.users.find({}, {"email":1, "mobile":1}).to_list(10)
        print("🔎 Current Database State:")
        for u in users:
            print(f"   User: {u.get('email')} -> Mobile: {u.get('mobile')}")
            
    except Exception as e:
        print(f"❌ Error during repair: {e}")
    finally:
        print("🛠️ Repair Finished.")

if __name__ == "__main__":
    asyncio.run(repair_database())
