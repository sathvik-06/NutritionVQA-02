import os
import re
from typing import Optional
from config.settings import settings

_UUID = re.compile(
    r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(\.[a-z0-9]+)?$", re.I
)


def normalize_image_url(image_id: Optional[str] = None, image_url: Optional[str] = None) -> Optional[str]:
    if image_id:
        m = _UUID.match(image_id.strip().split("/")[-1])
        if m:
            uid, ext = m.group(1), m.group(2)
            if ext:
                p = os.path.join(settings.UPLOAD_DIR, f"{uid}{ext.lower()}")
                return f"/uploads/{uid}{ext.lower()}" if os.path.isfile(p) else None
            for e in (".jpg", ".jpeg", ".png", ".webp"):
                p = os.path.join(settings.UPLOAD_DIR, f"{uid}{e}")
                if os.path.isfile(p):
                    return f"/uploads/{uid}{e}"
    if image_url:
        name = image_url.strip().split("/")[-1]
        if name and os.path.isfile(os.path.join(settings.UPLOAD_DIR, name)):
            return f"/uploads/{name}"
    return None
