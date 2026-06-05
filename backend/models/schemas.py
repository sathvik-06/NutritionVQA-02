from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, date

# ─── Auth & User ───────────────────────────────────────────────────────────

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    mobile: str
    weight: float
    age: int
    password: str
    height: Optional[float] = None  # cm
    gender: Optional[str] = None  # male/female/other
    health_goals: Optional[List[str]] = []  # weight_loss, muscle_gain, diabetes_management, etc.
    dietary_restrictions: Optional[List[str]] = []  # lactose_intolerant, gluten_free, vegan, etc.
    allergens: Optional[List[str]] = []  # nuts, dairy, shellfish, soy, etc.

class UserSignin(BaseModel):
    login: str  # Email or mobile number
    password: str

class UserProfileUpdate(BaseModel):
    """For updating user profile with health goals, restrictions, etc."""
    height: Optional[float] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    health_goals: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    allergens: Optional[List[str]] = None

class UserProfile(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    mobile: str
    weight: float
    age: int
    height: Optional[float] = None
    gender: Optional[str] = None
    health_goals: List[str] = []
    dietary_restrictions: List[str] = []
    allergens: List[str] = []
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    mobile: str

class VerifyOTPRequest(BaseModel):
    mobile: str
    otp: str

class ResetPasswordRequest(BaseModel):
    mobile: str
    otp: str
    new_password: str

class VerifySigninOTPRequest(BaseModel):
    login: str
    otp: str

class VerifySignupOTPRequest(UserSignup):
    otp: str

# ─── Notifications ─────────────────────────────────────────────────────────

class Notification(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    message: str
    type: str = "info"  # info, success, warning
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ─── Chat History ──────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "bot"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    image_id: Optional[str] = None
    image_urls: Optional[List[str]] = None
    nutrition_data: Optional[Dict[str, Any]] = None
    health_score: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class Conversation(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    title: str
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ─── Existing Endpoints ───────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str = Field(..., description="The nutrition question to ask.")
    image_id: Optional[str] = Field(None, description="Single uploaded label image ID.")
    image_ids: Optional[List[str]] = Field(None, description="Up to 3 uploaded label image IDs.")
    conversation_id: Optional[str] = Field(None, description="Chat conversation ID.")


class ImageUploadResponse(BaseModel):
    image_id: str
    image_url: Optional[str] = None
    crop_url: Optional[str] = None
    preprocess_url: Optional[str] = None
    ocr_text: str
    cleaned_ocr_text: Optional[str] = None
    nutrition_data: Dict[str, Any]
    confidence: str = "Low"
    confidence_score: Optional[float] = None
    confidence_warning: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_quality_score: Optional[float] = None
    ocr_readiness: Optional[float] = None
    ocr_debug: Optional[Dict[str, Any]] = None
    message: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    explanation: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_data: Optional[Dict[str, Any]] = None
    confidence: str = "Medium"

# ─── Daily Intake Tracker ────────────────────────────────────────────────

# ─── Product Comparator ──────────────────────────────────────────────────

class CompareRequest(BaseModel):
    """Request model for comparing two products."""
    image_id_a: str = Field(..., description="Image ID of product A.")
    image_id_b: str = Field(..., description="Image ID of product B.")

class AnalyzeRequest(BaseModel):
    """Request model for analyzing a single product's health impact."""
    image_id: str = Field(..., description="Image ID of the product.")

class CompareResponse(BaseModel):
    """Response model for product comparison."""
    product_a: Dict[str, Any] = {}
    product_b: Dict[str, Any] = {}
    comparison_table: List[Dict[str, Any]] = []
    ai_verdict: str = ""
    winner: Optional[str] = None

class AnalysisRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    image_id: str
    image_url: str
    nutrition_data: Dict[str, Any]
    health_verdict: str
    health_score: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ComparisonRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    image_id_a: str
    image_id_b: str
    image_url_a: str
    image_url_b: str
    data_a: Dict[str, Any]
    data_b: Dict[str, Any]
    comparison_table: List[Dict[str, Any]]
    ai_verdict: str
    winner: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
