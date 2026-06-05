import logging
from typing import Dict, Any

logger = logging.getLogger("state")

mistral_client = None
ocr_cache: Dict[str, Dict[str, Any]] = {}


def get_mistral_client():
    global mistral_client
    if mistral_client is None:
        from llm.mistral_client import MistralClient
        mistral_client = MistralClient()
    return mistral_client
