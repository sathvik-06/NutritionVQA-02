from fastapi import APIRouter, Depends, HTTPException, Query
from models.schemas import Conversation, ChatMessage
from auth.utils import get_current_user_email
from utils.database import get_async_db
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/api/chat", tags=["Chat History"])

@router.get("/history")
async def get_history(email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return all conversations for the user
    conversations = await db.conversations.find({"user_id": str(user["_id"])}).sort("updated_at", -1).to_list(100)
    
    # Convert MongoDB _id to string for JSON serialization
    for conv in conversations:
        conv["_id"] = str(conv["_id"])
    
    return conversations

@router.get("/{conv_id}")
async def get_conversation(conv_id: str, email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    # verify user owns the conversation
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        conv_obj_id = ObjectId(conv_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        
    conversation = await db.conversations.find_one({
        "_id": conv_obj_id, 
        "user_id": str(user["_id"])
    })
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conversation["_id"] = str(conversation["_id"])
    return conversation

@router.post("/save")
async def save_chat_message(msg: ChatMessage, conv_id: str = Query(None), email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    if conv_id:
        # Update existing conversation
        try:
            conv_obj_id = ObjectId(conv_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        
        await db.conversations.update_one(
            {"_id": conv_obj_id, "user_id": user_id},
            {
                "$push": {"messages": msg.dict()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return {"message": "Message saved to conversation", "conversation_id": conv_id}
    else:
        # Create a new conversation if it's the first message
        # Use first message content as title (truncated)
        title = msg.content[:30] + "..." if len(msg.content) > 30 else msg.content
        new_conv = {
            "user_id": user_id,
            "title": title,
            "messages": [msg.dict()],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.conversations.insert_one(new_conv)
        return {"message": "Message saved to new conversation", "conversation_id": str(result.inserted_id)}

@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        conv_obj_id = ObjectId(conv_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        
    await db.conversations.delete_one({"_id": conv_obj_id, "user_id": str(user["_id"])})
    return {"message": "Conversation deleted successfully"}