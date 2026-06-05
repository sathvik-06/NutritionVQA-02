"""
Feature Routes — All new feature endpoints in one organized router.
Covers: Comparator, Health Verdict, Profile Update.
"""
import logging
import json
import os
from datetime import datetime, timedelta
import re
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from auth.utils import get_current_user_email
from utils.database import get_async_db
from bson import ObjectId
from models.schemas import (
    CompareRequest, CompareResponse,
    UserProfileUpdate, AnalyzeRequest,
    AnalysisRecord, ComparisonRecord
)

logger = logging.getLogger("features")

router = APIRouter(prefix="/api/features", tags=["Features"])


# ─── Helper: get user doc ────────────────────────────────────────────────
async def _get_user(email: str):
    db = await get_async_db()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user, str(user["_id"])


# ═════════════════════════════════════════════════════════════════════════
# 1. PROFILE UPDATE (health goals, restrictions, allergens)
# ═════════════════════════════════════════════════════════════════════════

@router.put("/profile")
async def update_profile(data: UserProfileUpdate, email: str = Depends(get_current_user_email)):
    """Update user health profile with goals, restrictions, allergens."""
    db = await get_async_db()
    user, user_id = await _get_user(email)
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    await db.users.update_one({"_id": user["_id"]}, {"$set": update_data})
    return {"message": "Profile updated successfully", "updated_fields": list(update_data.keys())}


# ═════════════════════════════════════════════════════════════════════════
# 2. PERSONALIZED HEALTH ANALYZER
# ═════════════════════════════════════════════════════════════════════════

@router.post("/analyze")
async def analyze_product(req: AnalyzeRequest, email: str = Depends(get_current_user_email)):
    """Analyze a single product against user health profile."""
    from utils.state import ocr_cache, get_mistral_client
    
    if req.image_id not in ocr_cache:
        raise HTTPException(status_code=404, detail="Product data not found. Please upload it first.")
    
    user, user_id = await _get_user(email)
    nutrition_data = ocr_cache[req.image_id]["structured"]
    save_path = ocr_cache[req.image_id]["path"]
    
    # Generate image_url
    file_ext = os.path.splitext(save_path)[1]
    image_url = f"/uploads/{req.image_id}{file_ext}"

    mistral_client = get_mistral_client()
    verdict_data = await generate_health_verdict(nutrition_data, user, mistral_client)
    
    # Simple personalized health score calculation
    score = 85
    goals = user.get("health_goals", [])
    def parse_float(val):
        if not val or val == "N/A" or str(val).strip() == "":
            return 0.0
        match = re.search(r"(\d+\.?\d*)", str(val))
        return float(match.group(1)) if match else 0.0

    sugar = parse_float(nutrition_data.get("sugar", "0"))
    sodium = parse_float(nutrition_data.get("sodium", "0"))
    
    if sugar > 20: score -= 20
    if sodium > 800: score -= 15
    if "weight_loss" in goals and sugar > 10: score -= 10
    if "muscle_gain" in goals:
        protein = parse_float(nutrition_data.get("protein", "0"))
        if protein > 10: score += 5
    
    score = max(10, min(100, score))
    
    result = {
        "image_id": req.image_id,
        "nutrition_data": nutrition_data,
        "verdict": verdict_data["verdict"],
        "health_score": score
    }

    # Save to history
    db = await get_async_db()
    analysis_record = {
        "user_id": user_id,
        "image_id": req.image_id,
        "image_url": image_url,
        "nutrition_data": nutrition_data,
        "health_verdict": verdict_data["verdict"],
        "health_score": score,
        "created_at": datetime.utcnow()
    }
    await db.analyses.insert_one(analysis_record)

    return result


# ═════════════════════════════════════════════════════════════════════════
# 2. SIDE-BY-SIDE PRODUCT COMPARATOR
# ═════════════════════════════════════════════════════════════════════════

@router.post("/compare", response_model=CompareResponse)
async def compare_products(req: CompareRequest, email: str = Depends(get_current_user_email)):
    """Compare two scanned products side-by-side with AI verdict."""
    from utils.state import ocr_cache, get_mistral_client
    mistral_client = get_mistral_client()
    
    if req.image_id_a not in ocr_cache:
        raise HTTPException(status_code=404, detail="Product A not found. Please upload it first.")
    if req.image_id_b not in ocr_cache:
        raise HTTPException(status_code=404, detail="Product B not found. Please upload it first.")
    
    data_a = ocr_cache[req.image_id_a]["structured"]
    data_b = ocr_cache[req.image_id_b]["structured"]
    path_a = ocr_cache[req.image_id_a]["path"]
    path_b = ocr_cache[req.image_id_b]["path"]

    # URLs
    url_a = f"/uploads/{req.image_id_a}{os.path.splitext(path_a)[1]}"
    url_b = f"/uploads/{req.image_id_b}{os.path.splitext(path_b)[1]}"

    def get_base_key(k):
        for suffix in ["_g", "_mg", "_mcg", "_iu", "_pct"]:
            if k.endswith(suffix):
                return k[:-len(suffix)]
        return k

    base_keys = set()
    for k in data_a.keys():
        if k not in ("raw_text", "serving_size", "raw_transcription"):
            base_keys.add(get_base_key(k))
    for k in data_b.keys():
        if k not in ("raw_text", "serving_size", "raw_transcription"):
            base_keys.add(get_base_key(k))
    
    comparison_table = []
    a_wins = 0
    b_wins = 0
    
    def get_val_and_suffix(data, base):
        if base in data: return data[base], ""
        for suffix in ["_g", "_mg", "_mcg", "_iu", "_pct", "_kcal"]:
            if f"{base}{suffix}" in data: return data[f"{base}{suffix}"], suffix.replace("_", "")
        return "N/A", ""

    for b_key in sorted(base_keys):
        val_a, suf_a = get_val_and_suffix(data_a, b_key)
        val_b, suf_b = get_val_and_suffix(data_b, b_key)
        winner = None
        try:
            def clean_val(v):
                if v in ("N/A", "-", None): return None
                s = str(v).lower().replace(",", "").strip()
                import re
                is_less_than = "<" in s
                match = re.search(r"(\d+\.?\d*)", s)
                if not match: return None
                val = float(match.group(1))
                return val - 0.1 if is_less_than else val

            fa = clean_val(val_a)
            fb = clean_val(val_b)
            if fa is not None and fb is not None:
                if b_key in ("protein", "fiber"):
                    if fa > fb: winner = "A"; a_wins += 1
                    elif fb > fa: winner = "B"; b_wins += 1
                else:
                    if fa < fb: winner = "A"; a_wins += 1
                    elif fb < fa: winner = "B"; b_wins += 1
        except: pass
        
        def format_unit(v, k, suf):
            if v in ("N/A", "-", None) or str(v).strip() == "": return "N/A"
            s = str(v).strip()
            import re
            if re.search(r'[a-zA-Z%]$', s): return s
            if suf: return f"{s}{suf}"
            if k in ("calories", "energy"): return s
            if k in ("sodium", "cholesterol", "calcium", "iron", "potassium"): return f"{s}mg"
            return f"{s}g"

        comparison_table.append({
            "nutrient": b_key.replace("_", " ").title(),
            "product_a": format_unit(val_a, b_key, suf_a),
            "product_b": format_unit(val_b, b_key, suf_b),
            "winner": winner
        })
    
    overall_winner = "A" if a_wins > b_wins else "B" if b_wins > a_wins else "Tie"
    user, user_id = await _get_user(email)
    
    try:
        ai_verdict = await mistral_client.generate_comparison(data_a, data_b, user)
    except Exception:
        ai_verdict = f"Product {'A' if overall_winner == 'A' else 'B'} appears healthier based on nutrient categories."
    
    # Save to history
    db = await get_async_db()
    comp_record = {
        "user_id": user_id,
        "image_id_a": req.image_id_a,
        "image_id_b": req.image_id_b,
        "image_url_a": url_a,
        "image_url_b": url_b,
        "data_a": data_a,
        "data_b": data_b,
        "comparison_table": comparison_table,
        "ai_verdict": ai_verdict,
        "winner": overall_winner,
        "created_at": datetime.utcnow()
    }
    await db.comparisons.insert_one(comp_record)

    return CompareResponse(
        product_a=data_a,
        product_b=data_b,
        comparison_table=comparison_table,
        ai_verdict=ai_verdict,
        winner=overall_winner
    )


# ═════════════════════════════════════════════════════════════════════════
# 3. HISTORY ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════

@router.get("/history/analyses")
async def get_analyses_history(email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user, user_id = await _get_user(email)
    records = await db.analyses.find({"user_id": user_id}).sort("created_at", -1).to_list(50)
    for r in records: r["_id"] = str(r["_id"])
    return records

@router.get("/history/comparisons")
async def get_comparisons_history(email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user, user_id = await _get_user(email)
    records = await db.comparisons.find({"user_id": user_id}).sort("created_at", -1).to_list(50)
    for r in records: r["_id"] = str(r["_id"])
    return records

@router.delete("/history/analyses/{record_id}")
async def delete_analysis(record_id: str, email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user, user_id = await _get_user(email)
    await db.analyses.delete_one({"_id": ObjectId(record_id), "user_id": user_id})
    return {"message": "Analysis deleted"}

@router.delete("/history/comparisons/{record_id}")
async def delete_comparison(record_id: str, email: str = Depends(get_current_user_email)):
    db = await get_async_db()
    user, user_id = await _get_user(email)
    await db.comparisons.delete_one({"_id": ObjectId(record_id), "user_id": user_id})
    return {"message": "Comparison deleted"}


# ═════════════════════════════════════════════════════════════════════════
# 4. PERSONALIZED HEALTH VERDICT
# ═════════════════════════════════════════════════════════════════════════

async def generate_health_verdict(nutrition_data: Dict, user_profile: Dict, mistral_client) -> Dict:
    """Generate a personalized health verdict for a scanned product."""
    try:
        verdict = await mistral_client.generate_verdict(nutrition_data, user_profile)
        return {"verdict": verdict, "status": "ok"}
    except Exception as e:
        logger.error(f"Verdict generation failed: {e}")
        return _fallback_verdict(nutrition_data, user_profile)

def _fallback_verdict(nutrition_data: Dict, user_profile: Dict) -> Dict:
    """Simple rule-based verdict when AI is unavailable."""
    warnings = []
    positives = []
    
    # Default recommended values if profile is incomplete
    DAILY_RECOMMENDED = {
        "calories": 2000, "fat": 70, "saturated_fat": 20, "cholesterol": 300,
        "sodium": 2300, "carbohydrates": 275, "fiber": 28, "sugar": 50, "protein": 50
    }
    
    age = user_profile.get("age", 25)
    goals = user_profile.get("health_goals", [])
    
    def safe_float(val):
        if not val or val == "N/A" or str(val).strip() == "":
            return 0.0
        match = re.search(r"(\d+\.?\d*)", str(val))
        return float(match.group(1)) if match else 0.0

    sugar = nutrition_data.get("sugar")
    if sugar:
        sugar_val = safe_float(sugar)
        if sugar_val > 0:
            limit = 15 if "diabetes_management" in goals else 25
            pct = round(sugar_val / limit * 100)
            if pct > 50:
                warnings.append(f"Sugar is {pct}% of your daily limit ({sugar_val}g / {limit}g)")
            else:
                positives.append(f"Sugar is within acceptable range ({pct}% of daily limit)")
    
    sodium = nutrition_data.get("sodium")
    if sodium:
        sodium_val = safe_float(sodium)
        if sodium_val > 0:
            limit = 1500 if age > 50 else 2300
            pct = round(sodium_val / limit * 100)
            if pct > 30:
                warnings.append(f"Sodium is {pct}% of your daily limit ({sodium_val}mg / {limit}mg)")
    
    protein = nutrition_data.get("protein")
    if protein:
        prot_val = safe_float(protein)
        if prot_val >= 10:
            positives.append(f"Good protein content: {prot_val}g per serving")
    
    return {
        "verdict": "\n".join(
            [f"⚠️ {w}" for w in warnings] + [f"✅ {p}" for p in positives]
        ) or "No specific warnings for your profile.",
        "warnings": warnings,
        "positives": positives,
        "status": "fallback"
    }

