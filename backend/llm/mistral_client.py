"""
Mistral AI Client - generates nutrition answers using Mistral API.
(Boilerplate - full implementation in Step 5)
"""


import logging
import sys
import os
import json
import re
from typing import Dict, Any, List, Optional

# ─── Mistral SDK Patch (Handles both 0.x and 2.x versions) ───────────────────
try:
    # Try Modern 2.x SDK
    from mistralai.client import Mistral
    from mistralai.client.models import UserMessage, ChatCompletionResponse
    SDK_VERSION = 2
except ImportError:
    try:
        # Fallback to Legacy 0.x SDK
        from mistralai.client import MistralClient as Mistral
        from mistralai.models.chat_completion import ChatMessage as UserMessage
        SDK_VERSION = 0
    except ImportError:
        Mistral = None
        SDK_VERSION = -1

# ─── Config Import Patch ──────────────────────────────────────────────────────
try:
    from config.settings import settings
except ImportError:
    # Try to find config relative to this file
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from config.settings import settings
    except ImportError:
        # Try from backend
        try:
             from backend.config.settings import settings
        except ImportError:
             raise ImportError("Could not find 'config.settings'. Ensure your python path is set correctly.")

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("mistral")

class MistralClient:
    """Handles interaction with the Mistral AI API for expert nutrition answer generation."""

    EXTRACTION_SYSTEM_PROMPT = """You are a strict nutrition label extraction engine.

Your job is to extract ONLY nutrition values explicitly visible in OCR text.

STRICT RULES:
* Do NOT hallucinate
* Do NOT estimate
* Do NOT infer
* Do NOT calculate
* Do NOT use external knowledge
* Do NOT fill missing values
* Make sure the value is clear
* Ignore unrelated text
* Return ONLY valid JSON

Extract:
serving_size, calories, protein_g, fat_g, carbohydrates_g, sugar_g, fiber_g, sodium_mg"""

    PROMPT_TEMPLATE = """You are a nutrition expert AI.

Nutrition Data:
{ocr_data}

Knowledge:
{retrieved_context}

User Health Profile:
{user_context}

Question:
{user_question}

Think step-by-step.

Answer format:
Explanation:
...
Final Answer:
..."""

    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self._client = None
        self.model = settings.MISTRAL_MODEL

    def _get_client(self):
        """Lazy load the Mistral client."""
        if self._client is None:
            if not self.api_key:
                logger.warning("⚠️ MISTRAL_API_KEY is not set. API calls will fail.")

            if SDK_VERSION == 2:
                try:
                    import certifi
                    import httpx
                    async_client = httpx.AsyncClient(verify=certifi.where(), timeout=120.0)
                    self._client = Mistral(api_key=self.api_key, async_client=async_client)
                except TypeError:
                    self._client = Mistral(api_key=self.api_key)
            elif SDK_VERSION == 0:
                # For 0.x we use the async client as requested by original code
                from mistralai.async_client import MistralAsyncClient
                self._client = MistralAsyncClient(api_key=self.api_key)
            else:
                logger.error("❌ No Mistral SDK installed.")
        return self._client

    async def _chat_call(self, messages):
        return await self._chat_call_internal(messages)

    async def _chat_call_internal(self, messages, temperature=0.3):
        try:
            client = self._get_client()
            if SDK_VERSION == 2:
                # 120s timeout for stability
                res = await client.chat.complete_async(
                    model=self.model, 
                    messages=messages, 
                    temperature=temperature,
                    timeout_ms=120000 
                )
            else:
                res = await client.chat(
                    model=self.model, 
                    messages=messages, 
                    temperature=temperature,
                    request_timeout=120
                )
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Mistral API call error: {type(e).__name__}: {str(e)}")
            raise e

    async def generate_verdict(self, nutrition_data: Dict, user_profile: Dict) -> str:
        """Generate a personalized health verdict for a single scanned product."""
        try:
            client = self._get_client()
            if not client or not self.api_key:
                raise ValueError("API not configured")
                
            prompt = f"""You are a Clinical Nutritionist. Provide a comprehensive Expert Health Report for this product.

User Profile:
- Goals: {', '.join(user_profile.get('health_goals', []))}
- Restrictions: {', '.join(user_profile.get('dietary_restrictions', []))}
- Allergens: {', '.join(user_profile.get('allergens', []))}

Product Nutrition Data:
{json.dumps(nutrition_data, indent=2)}

TASK: Provide a structured expert report in Markdown:
### 🏥 Expert Health Report
1. **Health Score Rationale**: Explain why this product deserves its health score for this specific user.
2. **Nutritional Highlights (Pros)**: List 2-3 positive aspects relative to their specific health goals.
3. **Red Flags (Cons)**: List any values that conflict with their goals or restrictions.
4. **Therapeutic Recommendation**: A final professional verdict (e.g. ✅ Highly Recommended, ⚠️ Consume in Moderation, ❌ Avoid).
"""
            messages = [UserMessage(role="user", content=prompt)]
            res = await self._chat_call(messages)
            return res
        except Exception as e:
            logger.warning(f"⚠️ AI Verdict failed ({e}), using local rule-based fallback.")
            return self._local_verdict(nutrition_data)

    def _parse_num(self, val) -> float:
        if val is None or val == "" or str(val).strip() in ("N/A", "NA"):
            return 0.0
        match = re.search(r"(\d+\.?\d*)", str(val))
        return float(match.group(1)) if match else 0.0

    def _local_verdict(self, data: Dict) -> str:
        """Fallback nutrition logic when API is unavailable."""
        res = "### 🏷️ Local Analysis (Demo Mode)\n\n"
        sugar = self._parse_num(data.get("sugar"))
        sodium = self._parse_num(data.get("sodium"))
        protein = self._parse_num(data.get("protein"))
        
        if sugar > 15: res += "* ⚠️ **High Sugar Alert:** This product contains significant sugar.\n"
        if sodium > 500: res += "* ⚠️ **Sodium Warning:** High salt content detected.\n"
        if protein > 10: res += "* ✅ **Protein Rich:** Good source of protein for muscle health.\n"
        
        res += "\n**Recommendation:** "
        if sugar > 20 or sodium > 800: res += "❌ Avoid or limit consumption."
        else: res += "⚠️ Consume in moderation as part of a balanced diet."
        return res

    async def generate_comparison(self, data_a: Dict, data_b: Dict, user_profile: Dict) -> str:
        """Generate a side-by-side comparison verdict for two products."""
        try:
            client = self._get_client()
            if not client or not self.api_key:
                raise ValueError("Mistral API key is missing or invalid.")

            # Validate data
            if not data_a or not data_b:
                return "Insufficient data to perform comparison. Please ensure both labels are clearly scanned."

            prompt = f"""You are a Clinical Nutritionist and Comparison Expert.
Compare these two products side-by-side for a user with these goals: {', '.join(user_profile.get('health_goals', []))}.

Product A Data:
{json.dumps(data_a, indent=2)}

Product B Data:
{json.dumps(data_b, indent=2)}

TASK: Provide a comprehensive comparison report:
### ⚖️ Clinical Comparison Report

1. **Direct Head-to-Head**: Compare key nutrients (Calories, Sugar, Protein, Sodium) and explain which product wins each category for this specific user.
2. **Overall Nutritional Superiority**: Which product has a better overall profile (e.g., fewer additives, better macro balance)?
3. **The Professional Winner**: Declare a clear "Winner" (Product A or Product B) and provide a concise summary of why it is the better choice for the user's goals.
4. **Final Recommendation**: How should the user incorporate the winner into their diet?
"""
            messages = [UserMessage(role="user", content=prompt)]
            logger.info(f"⚖️ Sending comparison request to Mistral...")
            res = await self._chat_call(messages)
            return res
        except Exception as e:
            logger.error(f"❌ AI Comparison failed: {type(e).__name__}: {str(e)}")
            return "### ⚖️ Comparison Verdict (Local Fallback)\n\n" \
                   "The AI comparison service is currently unavailable. " \
                   "Please refer to the side-by-side nutrient table above to compare the values manually. " \
                   "Generally, look for lower sugar/sodium and higher protein/fiber."

    def _parse_extraction_json(self, content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```\s*$", "", text)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        raw_json = m.group(0)
        try:
            parsed = json.loads(raw_json, strict=False)
        except json.JSONDecodeError:
            # Fallback: escape unescaped control characters inside string values
            sanitized = re.sub(
                r'(?<=": ")(.*?)(?="[,\s\}])',
                lambda mat: mat.group(0).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"),
                raw_json,
                flags=re.DOTALL,
            )
            try:
                parsed = json.loads(sanitized, strict=False)
            except Exception as e2:
                logger.error(f"Failed to parse json block even after sanitization: {e2}")
                return {}
        except Exception as e:
            logger.error(f"Failed to parse json block: {e}")
            return {}

        std = {k.lower().replace(" ", "_"): v for k, v in parsed.items()}
        
        # Mapping base names and variations to ensure both unsuffixed and suffixed keys exist
        groups = {
            "protein": ["protein", "protein_g"],
            "protein_g": ["protein", "protein_g"],
            "fat": ["fat", "total_fat", "fat_g"],
            "total_fat": ["fat", "total_fat", "fat_g"],
            "fat_g": ["fat", "total_fat", "fat_g"],
            "carbohydrates": ["carbohydrates", "carbohydrates_g"],
            "carbohydrates_g": ["carbohydrates", "carbohydrates_g"],
            "sugar": ["sugar", "sugar_g"],
            "sugar_g": ["sugar", "sugar_g"],
            "fiber": ["fiber", "fiber_g"],
            "fiber_g": ["fiber", "fiber_g"],
            "sodium": ["sodium", "sodium_mg"],
            "sodium_mg": ["sodium", "sodium_mg"],
            "serving_size": ["serving_size"],
            "calories": ["calories"],
            "raw_transcription": ["raw_transcription"]
        }

        out: Dict[str, Any] = {}
        for k, v in std.items():
            if v is None or str(v).strip().upper() in ("N/A", "NULL", "NONE", ""):
                continue
            
            if k in groups:
                for target_key in groups[k]:
                    out[target_key] = v
            else:
                out[k] = v
        return out

    async def parse_nutrition_json(self, cleaned_ocr_text: str) -> Dict[str, Any]:
        """Mistral 7B extraction from cleaned OCR only (no RAG)."""
        if not (cleaned_ocr_text or "").strip():
            raise ValueError("OCR text is empty")
        client = self._get_client()
        if not client or not self.api_key:
            raise ValueError("MISTRAL_API_KEY not configured")
        user = f"OCR TEXT:\n{cleaned_ocr_text[:6500]}"
        if SDK_VERSION == 2:
            messages = [
                {"role": "system", "content": self.EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ]
        else:
            messages = [UserMessage(role="user", content=f"{self.EXTRACTION_SYSTEM_PROMPT}\n\n{user}")]
        content = await self._chat_call_internal(messages, temperature=0.0)
        result = self._parse_extraction_json(content)
        if not result:
            raise ValueError("Mistral returned no valid JSON")
        return result

    async def extract_from_image(self, image_path: str) -> tuple:
        """Directly extract nutrition facts from an image using Mistral Vision (Pixtral) via httpx REST API."""
        import base64
        import httpx

        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not configured")

        with open(image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.rsplit(".", 1)[-1].lower()
        mime = {"jpeg": "image/jpeg", "jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")

        vision_prompt = (
            "Read this entire nutrition label exactly as it appears. "
            "Do NOT crop, skip, or modify any part of the label. "
            "Do NOT modify any values or numbers. "
            "Output a valid JSON object with these keys: "
            "serving_size, calories, protein_g, fat_g, carbohydrates_g, sugar_g, fiber_g, sodium_mg. "
            "Also include a key 'raw_transcription' containing the full verbatim text from the label as a single string."
        )

        payload = {
            "model": "pixtral-12b-2409",
            "messages": [
                {"role": "system", "content": self.EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": vision_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}}
                ]}
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        logger.info("✅ Pixtral Vision response received (%d chars)", len(content))

        result = self._parse_extraction_json(content)
        if not result:
            raise ValueError(f"Pixtral returned no valid JSON. Raw: {content[:500]}")
        return result, content

    async def generate_answer(
        self,
        question: str,
        ocr_data: Any = "No image data provided.",
        user_profile: Optional[Dict] = None,
        retrieved_context: str = "",
    ) -> Dict[str, Any]:
        """Generate expert nutrition answer with API failure protection."""
        try:
            client = self._get_client()
            if not client or not self.api_key:
                raise ValueError("API key missing")

            # Format the prompt
            if isinstance(ocr_data, list) and len(ocr_data) > 1:
                # Handle multiple products (A, B, C...)
                ocr_str = ""
                for i, data in enumerate(ocr_data):
                    label = chr(65 + i) # A, B, C...
                    ocr_str += f"### Product {label}:\n{json.dumps(data, indent=2)}\n\n"
            elif isinstance(ocr_data, list) and len(ocr_data) == 1:
                ocr_str = json.dumps(ocr_data[0], indent=2)
            else:
                ocr_str = json.dumps(ocr_data, indent=2) if isinstance(ocr_data, dict) else str(ocr_data)

            # Format User Context
            user_context = "No specific user health profile provided."
            if user_profile:
                user_context = f"- Name: {user_profile.get('name')}\n" \
                               f"- Age: {user_profile.get('age')}\n" \
                               f"- Weight: {user_profile.get('weight')} kg\n" \
                               f"- Goals: {', '.join(user_profile.get('health_goals', []))}\n" \
                               f"- Restrictions: {', '.join(user_profile.get('dietary_restrictions', []))}\n" \
                               f"- Allergens: {', '.join(user_profile.get('allergens', []))}"

            prompt = self.PROMPT_TEMPLATE.format(
                ocr_data=ocr_str,
                retrieved_context=retrieved_context or "No additional expert knowledge retrieved.",
                user_context=user_context,
                user_question=question
            )

            messages = [UserMessage(role="user", content=prompt)]
            logger.info(f"🤖 Sending prompt to Mistral AI...")
            
            content = await self._chat_call(messages)
            logger.info("✅ Received response from Mistral AI")

            parts = re.split(r'Final Answer:|FINAL ANSWER:', content, flags=re.IGNORECASE)
            explanation = parts[0].replace("Explanation:", "").replace("EXPLANATION:", "").strip() if len(parts) > 1 else ""
            final_answer = parts[1].strip() if len(parts) > 1 else content
            
            # If AI didn't provide Explanation header, but provided Final Answer
            if not explanation and "Explanation:" not in content and len(parts) > 1:
                explanation = "AI Nutrition Analysis"

            return {"answer": final_answer, "explanation": explanation, "raw_response": content}

        except Exception as e:
            logger.error(f"❌ Mistral API call failed: {e}. Switching to local logic.")
            # Fallback answer based on the context
            try:
                if isinstance(ocr_data, list) and len(ocr_data) > 0:
                    val_data = ocr_data[0]
                elif isinstance(ocr_data, dict):
                    val_data = ocr_data
                else:
                    val_data = {}
                
                if isinstance(val_data, dict):
                    return {
                        "answer": f"Based on the label data, this product has {val_data.get('calories','N/A')} calories and {val_data.get('sugar','N/A')}g of sugar. (Demo Fallback)",
                        "explanation": "The AI API is currently offline, so I'm providing a direct data summary.",
                        "raw_response": ""
                    }
            except Exception:
                pass
            
            # Last resort fallback
            return {
                "answer": "The AI API is currently offline. Please try again later or refer to the nutrition label directly.",
                "explanation": "Service temporarily unavailable.",
                "raw_response": ""
            }