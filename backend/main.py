import os
import sys
import asyncio

# Fix for Windows asyncio loop (ConnectionResetError 10054 noise)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ─── Paddle & Torch Dependency Fix ──────────────────────────────────────────
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_mkldnn"] = "0"
os.environ["PADDLE_ENABLE_ONEDNN"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PIR_API"] = "0"
os.environ["FLAGS_new_executor"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["PADDLE_DISABLE_CUDA"] = "1"
os.environ["FLAGS_ir_optim_pass_one_mkl_dnn_pass_filter"] = ""
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def _lazy_init_paddle():
    """Load Paddle & Torch in background AFTER server is already accepting requests."""
    try:
        import torch
        import paddle
        paddle.set_flags({
            "FLAGS_use_mkldnn": 0,
            "FLAGS_enable_mkldnn": 0,
            "FLAGS_use_onednn": 0,
            "FLAGS_enable_pir_api": 0,
            "FLAGS_enable_pir_in_executor": 0
        })
        paddle.set_device('cpu')
    except:
        pass

# ─── Avast Antivirus SSL Fix ──────────────────────────────────────────────────
os.environ.pop("SSLKEYLOGFILE", None)
os.environ["SSLKEYLOGFILE"] = ""
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

# ─── Legacy LangChain Patch for PaddleOCR/PaddleX ─────────────────────────────
try:
    import langchain_core.documents as docs
    import types
    doc_mod = types.ModuleType("langchain.docstore.document")
    doc_mod.Document = docs.Document
    sys.modules["langchain.docstore"] = types.ModuleType("langchain.docstore")
    sys.modules["langchain.docstore.document"] = doc_mod
    import langchain_text_splitters
    sys.modules["langchain.text_splitter"] = langchain_text_splitters
except ImportError:
    pass

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

# ─── Config & Local Imports ──────────────────────────────────────────────────
# Add the current directory to sys.path to ensure 'config', 'models', etc. are found
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    from config.settings import settings
    from models.schemas import QuestionRequest, ImageUploadResponse, AnswerResponse
    from utils.database import get_async_db, close_async_db
    from utils.cache import close_redis
    from auth.routes import router as auth_router
    from auth.utils import get_current_user_email
    from features.routes import router as features_router
    from chat.routes import router as chat_router
except ImportError:
    # Fallback for different working directories
    from .config.settings import settings
    from .models.schemas import QuestionRequest, ImageUploadResponse, AnswerResponse
    from .utils.database import get_async_db, close_async_db
    from .utils.cache import close_redis
    from .auth.routes import router as auth_router
    from .auth.utils import get_current_user_email
    from .features.routes import router as features_router
    from .chat.routes import router as chat_router

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("nutritionvqa")

# Silence noisy uvicorn access logs (prevents 200 and 304 spam in terminal)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting NutritionVQA server …")
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Connect to MongoDB in the background to prevent blocking server startup
    try:
        asyncio.create_task(get_async_db())
    except Exception as e:
        logger.error(f"⚠️ MongoDB connection failed: {e}")

    # Pre-initialize heavy AI components
    try:
        from utils.state import get_mistral_client
        logger.info("🧠 Pre-loading Mistral client...")
        get_mistral_client()
        logger.info("✅ Mistral client pre-loaded.")
    except Exception as ai_err:
        logger.warning(f"⚠️ Mistral pre-loading failed: {ai_err}")
    
    logger.info("✅ Server ready and accepting requests!")
    
    # Removed heavy ML lib background loading to significantly speed up startup time
    yield
    # Shutdown
    await close_async_db()
    await close_redis()
    logger.info("🛑 Server stopped")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NutritionVQA API",
    description="Strict OCR-based nutrition label extraction",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Cache Busting Middleware (for Debug Mode) ────────────────────────────────
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    # Skip WebSocket requests to avoid Starlette StaticFiles AssertionError
    if request.scope.get("type") != "http":
        return await call_next(request)
        
    response = await call_next(request)
    if settings.DEBUG:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api", tags=["Health"])
async def root():
    return {"status": "ok", "service": "NutritionVQA API", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools_silence():
    return JSONResponse(content={})


# ─── Static Files for Frontend ────────────────────────────────────────────────
# Frontend is served via StaticFiles mount at the very end of this file
# (must be last so API routes take priority over the catch-all "/" mount)
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


import uuid
import shutil
from typing import Dict, Any, Optional

from utils.state import ocr_cache, get_mistral_client
from utils.media_urls import normalize_image_url

EXTRACTION_ERROR = {"error": "Unable to extract nutrition values reliably"}

# ─── Include Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(features_router)
app.include_router(chat_router)


# ─── Upload Image Endpoint ───────────────────────────────────────────────────────────

@app.post("/upload-image", response_model=ImageUploadResponse, tags=["Vision"])
async def upload_image(
    file: UploadFile = File(...),
    email: str = Depends(get_current_user_email),
):
    """Extract nutrition data from a label image using Mistral Vision (Pixtral)."""
    _ = email
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    try:
        # Save the uploaded file
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not settings.MISTRAL_API_KEY:
            raise HTTPException(status_code=503, detail="MISTRAL_API_KEY is not configured.")

        # Use Mistral Vision (Pixtral) for extraction
        logger.info("🚀 Sending image to Pixtral Vision for extraction...")
        mc = get_mistral_client()
        ai_data, vision_raw = await mc.extract_from_image(save_path)

        # Extract verbatim transcription from the AI response
        raw_text = ai_data.pop("raw_transcription", vision_raw)
        cleaned = raw_text

        # Compute simple confidence
        has_values = sum(1 for v in ai_data.values() if v is not None)
        if has_values >= 5:
            conf_level, conf_score = "High", 0.9
        elif has_values >= 3:
            conf_level, conf_score = "Medium", 0.6
        else:
            conf_level, conf_score = "Low", 0.3

        nutrition_json = ai_data
        if not any(v is not None for v in nutrition_json.values()):
            nutrition_json = dict(EXTRACTION_ERROR)

        ocr_cache[file_id] = {"text": raw_text, "cleaned": cleaned, "structured": nutrition_json, "path": save_path}
        return ImageUploadResponse(
            image_id=file_id,
            image_url=normalize_image_url(file_id) or f"/uploads/{file_id}{file_ext}",
            ocr_text=raw_text,
            cleaned_ocr_text=cleaned,
            nutrition_data=nutrition_json,
            confidence=conf_level,
            confidence_score=conf_score,
            message="Label processed successfully." if "error" not in nutrition_json else "Could not extract reliably.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=AnswerResponse, tags=["QA"])
async def ask_question(request: QuestionRequest, email: str = Depends(get_current_user_email)):
    """Answer using OCR label data and RAG expert knowledge."""
    mc = get_mistral_client()
    req_ids = request.image_ids or ([request.image_id] if request.image_id else [])
    contexts = [ocr_cache[i]["structured"] for i in req_ids if i in ocr_cache]
    ocr_data = contexts[0] if len(contexts) == 1 else contexts if contexts else "No label uploaded."
    
    # ─── RAG Context Retrieval ────────────────────────────────────────────────
    retrieved_contexts = []
    retrieved_context_str = ""
    try:
        from rag.retriever import get_retriever
        retriever = get_retriever()
        retrieved_contexts = await retriever.retrieve(request.question, k=5)
        if retrieved_contexts:
            retrieved_context_str = "\n\n".join(retrieved_contexts)
            logger.info(f"📚 Retrieved {len(retrieved_contexts)} contexts for question: '{request.question}'")
    except Exception as rag_err:
        logger.error(f"⚠️ RAG retrieval failed: {rag_err}. Falling back to OCR-only mode.")
        retrieved_context_str = ""

    db = await get_async_db()
    profile = await db.users.find_one({"email": email}) if db is not None else None
    
    result = await mc.generate_answer(
        request.question, 
        ocr_data=ocr_data, 
        user_profile=profile,
        retrieved_context=retrieved_context_str
    )
    
    sources = [{"text": ctx} for ctx in retrieved_contexts]
    
    return AnswerResponse(
        question=request.question,
        answer=result.get("answer", ""),
        explanation=result.get("explanation", ""),
        sources=sources,
        ocr_data=ocr_data if isinstance(ocr_data, (dict, list)) else None,
        confidence="Low" if isinstance(ocr_data, dict) and ocr_data.get("error") else "Medium",
    )



# ─── Catch-all Static Files for Frontend ──────────────────────────────────────
# Mounted last so API endpoints take priority
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    logger.warning(f"⚠️ Frontend directory not found at: {frontend_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT
    )



