from fastapi import APIRouter, Depends, HTTPException, status
from models.schemas import UserSignup, UserSignin, Token, ForgotPasswordRequest, VerifyOTPRequest, ResetPasswordRequest, VerifySigninOTPRequest, VerifySignupOTPRequest
from auth.utils import get_password_hash, verify_password, create_access_token, get_current_user_email
from utils.database import get_async_db
from datetime import datetime, timedelta
import random
import logging

from config.settings import settings

try:
    from sms.twilio_service import twilio_service
except ImportError:
    twilio_service = None
    print("⚠️ sms.twilio_service not found — OTP via SMS will be unavailable")

try:
    from notifications.rabbitmq import rabbitmq_service
except ImportError:
    rabbitmq_service = None

logger = logging.getLogger("nutritionvqa.auth")

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup")
async def signup(user_data: UserSignup):
    if not user_data.email.lower().endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Only official @gmail.com addresses are supported.")
    
    db = await get_async_db()
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"mobile": user_data.mobile}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="An account already exists with this Gmail. Please sign in.")
    
    # 2FA: Generate and send OTP for signup
    otp = str(random.randint(100000, 999999))
    user_mobile = user_data.mobile
    
    await db.otp_tokens.replace_one(
        {"mobile": user_mobile},
        {"mobile": user_mobile, "otp": otp, "expires_at": datetime.utcnow() + timedelta(minutes=10)},
        upsert=True
    )
    
    success = twilio_service and await twilio_service.send_otp(user_mobile, otp)
    if not success:
        logger.warning(f"OTP FALLBACK FOR SIGNUP {user_mobile}: {otp}")
        return {
            "message": "OTP generated. If SMS was not received, check server logs.",
            "require_otp": True,
            "dev_otp": otp if settings.DEBUG else None
        }
        
    return {"message": "Verification code sent to your mobile", "require_otp": True}


@router.post("/verify-signup-otp")
async def verify_signup_otp(user_data: VerifySignupOTPRequest):
    db = await get_async_db()
    user_mobile = user_data.mobile
    
    otp_data = await db.otp_tokens.find_one({"mobile": user_mobile, "otp": user_data.otp})
    if not otp_data or otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    # Valid OTP, proceed with account creation
    hashed_password = get_password_hash(user_data.password)
    user_doc = user_data.dict(exclude={"otp"})
    user_doc["password"] = hashed_password
    user_doc["created_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    await db.otp_tokens.delete_one({"mobile": user_mobile})
    
    return {"message": "User created successfully", "user_id": user_id}


@router.post("/signin")
async def signin(user_data: UserSignin):
    if "@" in user_data.login and not user_data.login.lower().endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Please use a valid @gmail.com address.")

    db = await get_async_db()
    user = await db.users.find_one({
        "$or": [{"email": user_data.login}, {"mobile": user_data.login}]
    })
    if not user:
        raise HTTPException(status_code=401, detail="Gmail not registered. Please create an account first.")

    password_ok = verify_password(user_data.password, user["password"])
    
    if not password_ok:
        logger.warning(f"Signin failed: invalid password for {user_data.login}")
        raise HTTPException(status_code=401, detail="Invalid password")
        
    # 2FA: Generate and send OTP for signin
    otp = str(random.randint(100000, 999999))
    user_mobile = user.get("mobile", "N/A")
        
    await db.otp_tokens.replace_one(
        {"mobile": user_mobile},
        {"mobile": user_mobile, "otp": otp, "expires_at": datetime.utcnow() + timedelta(minutes=10)},
        upsert=True
    )
    
    success = False
    if user_mobile != "N/A":
        success = twilio_service and await twilio_service.send_otp(user_mobile, otp)
        
    if not success:
        logger.warning(f"OTP FALLBACK FOR SIGNIN {user_mobile}: {otp}")
        return {
            "message": "OTP generated. Since no mobile is linked or Twilio failed, use the Dev OTP.",
            "require_otp": True,
            "dev_otp": otp
        }
        
    return {"message": "Verification code sent to your mobile", "require_otp": True}


@router.post("/verify-signin-otp", response_model=Token)
async def verify_signin_otp(req: VerifySigninOTPRequest):
    db = await get_async_db()
    
    # Find user by email or mobile to get their actual mobile number
    user = await db.users.find_one({
        "$or": [{"email": req.login}, {"mobile": req.login}]
    })
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    user_mobile = user.get("mobile")
    otp_data = await db.otp_tokens.find_one({"mobile": user_mobile, "otp": req.otp})
    if not otp_data or otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    await db.otp_tokens.delete_one({"mobile": user_mobile})
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    db = await get_async_db()
    # 1. Extract exactly the last 10 digits from the input
    only_digits = "".join(filter(str.isdigit, req.mobile))
    if len(only_digits) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid 10-digit mobile number.")
    
    last_10 = only_digits[-10:]
    logger.info(f"🔎 DEBUG: Strict Mobile Search for: ...{last_10}")

    # 2. Search MongoDB for ANY user whose mobile number ends with these 10 digits
    user = await db.users.find_one({
        "mobile": {"$regex": f"{last_10}$"}
    })
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"No account found with mobile number ending in {last_10}. Please check your number and try again."
        )
    
    # 3. Generate and Send OTP strictly via SMS
    otp = str(random.randint(100000, 999999))
    user_mobile = user.get("mobile") # Use the mobile number EXACTLY as stored in DB
    
    logger.info(f"📲 Sending OTP to found user: {user_mobile}")
    # Store OTP in DB with expiration
    await db.otp_tokens.replace_one(
        {"mobile": user_mobile},
        {"mobile": user_mobile, "otp": otp, "expires_at": datetime.utcnow() + timedelta(minutes=10)},
        upsert=True
    )
    
    success = twilio_service and await twilio_service.send_otp(user_mobile, otp)
    if not success:
        logger.warning(f"OTP FALLBACK for {user_mobile}: {otp}")
        return {
            "message": "OTP generated. If SMS was not received, use the code shown in server logs (dev mode).",
            "dev_otp": otp if settings.DEBUG else None,
        }
        
    return {"message": "OTP sent to your registered mobile number"}

@router.post("/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    db = await get_async_db()
    # Find the user's canonical mobile number first
    only_digits = "".join(filter(str.isdigit, req.mobile))
    last_10 = only_digits[-10:]
    user = await db.users.find_one({"mobile": {"$regex": f"{last_10}$"}})
    
    if not user:
        raise HTTPException(status_code=404, detail="Mobile number not found")
    
    user_mobile = user["mobile"]
    otp_data = await db.otp_tokens.find_one({"mobile": user_mobile, "otp": req.otp})
    
    if not otp_data:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    db = await get_async_db()
    # Find the user's canonical mobile number first
    only_digits = "".join(filter(str.isdigit, req.mobile))
    last_10 = only_digits[-10:]
    user = await db.users.find_one({"mobile": {"$regex": f"{last_10}$"}})
    
    if not user:
        raise HTTPException(status_code=404, detail="Mobile number not found")
        
    user_mobile = user["mobile"]
    otp_data = await db.otp_tokens.find_one({"mobile": user_mobile, "otp": req.otp})
    if not otp_data or otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    hashed_password = get_password_hash(req.new_password)
    await db.users.update_one({"mobile": user_mobile}, {"$set": {"password": hashed_password}})
    await db.otp_tokens.delete_one({"mobile": user_mobile})
    
    return {"message": "Password reset successfully"}

@router.post("/google/send-otp")
async def send_google_otp(data: dict):
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    mobile = data.get("mobile")
    
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    
    if user:
        db_mobile = user.get("mobile")
        if db_mobile and db_mobile != "N/A":
            mobile = db_mobile
            
    if not mobile or mobile == "N/A":
        # Fallback if no mobile is provided or found
        otp = str(random.randint(100000, 999999))
        return {
            "message": "No mobile number linked. Use Dev OTP.",
            "dev_otp": otp if settings.DEBUG else None
        }

    otp = str(random.randint(100000, 999999))
    
    # Store in DB for verification
    await db.otp_tokens.replace_one(
        {"email": email},
        {"email": email, "otp": otp, "expires_at": datetime.utcnow() + timedelta(minutes=10)},
        upsert=True
    )
    
    # SEND REAL OTP VIA TWILIO
    success = twilio_service and await twilio_service.send_otp(mobile, otp)
    if not success:
        logger.warning(f"TWILIO FALLBACK OTP FOR {mobile}: {otp}")
        return {
            "message": "OTP sent via simulated SMS (check server logs if Twilio unavailable)",
            "dev_otp": otp if settings.DEBUG else None,
        }
    
    return {
        "message": "Verification code sent to your mobile via Twilio",
        "dev_otp": otp if settings.DEBUG else None
    }

from pydantic import BaseModel

class GoogleAuthRequest(BaseModel):
    token: str
    otp: str = None

@router.post("/google")
async def google_auth(data: GoogleAuthRequest):
    token = data.token
    otp = data.otp
    if not token:
        raise HTTPException(status_code=400, detail="Google token is required")
        
    try:
        # Decode the JWT payload without verifying signature (for testing/demo)
        # Note: In production, verify the token signature and audience using google-auth.
        header, payload, sig = token.split(".")
        padded_payload = payload + "=" * ((4 - len(payload) % 4) % 4)
        import base64, json
        decoded_bytes = base64.urlsafe_b64decode(padded_payload)
        token_data = json.loads(decoded_bytes)
        email = token_data.get("email")
        name = token_data.get("name", "Google User")
        mock_password = token_data.get("password", "GOOGLE_AUTH_NO_PASSWORD")
        mock_mobile = token_data.get("mobile", "N/A")
    except Exception as e:
        logger.error(f"Failed to decode Google token: {e}")
        raise HTTPException(status_code=400, detail="Invalid Google token")

    if not email:
        raise HTTPException(status_code=400, detail="Token did not contain an email")

    if not otp:
        raise HTTPException(status_code=400, detail="OTP is required for 2FA")

    db = await get_async_db()
    
    otp_data = await db.otp_tokens.find_one({"email": email, "otp": otp})
    if not otp_data or otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Clean up OTP after successful verification
    await db.otp_tokens.delete_one({"email": email})

    user = await db.users.find_one({"email": email})
    
    if not user:
        # Auto-create user for Google Sign-In with real password for interoperability
        user_doc = {
            "name": name,
            "email": email,
            "mobile": mock_mobile,
            "password": get_password_hash(mock_password),
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(user_doc)
        return {"message": "Account created successfully. Please log in.", "is_new_user": True}
    
    access_token = create_access_token(data={"sub": email})
    
    return {"access_token": access_token, "token_type": "bearer", "is_new_user": False}


@router.get("/me")
async def get_current_user(email: str = Depends(get_current_user_email)):
    """Return the currently logged-in user's profile."""
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "name": user.get("name", "User"),
        "email": user.get("email", ""),
        "mobile": user.get("mobile", ""),
        "weight": user.get("weight", 0),
        "age": user.get("age", 0),
        "health_goals": user.get("health_goals", []),
        "dietary_restrictions": user.get("dietary_restrictions", []),
        "allergens": user.get("allergens", []),
    }