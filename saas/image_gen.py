"""
AI Image Generation — routes to the correct model per subscription tier.
Supports: DALL-E 3 (OpenAI), FLUX/Ideogram/SD (fal.ai), Imagen 3 (Google).
Admin configures which model each tier uses via the admin panel.
"""
import os, base64
from typing import Optional
import saas.db as db

# Platform-specific aspect ratios
DALLE_PLATFORM_SIZES = {
    "facebook":  "1024x1024",
    "instagram": "1024x1024",
    "linkedin":  "1792x1024",
    "twitter":   "1792x1024",
    "tiktok":    "1024x1792",
}

STYLE_MAP = {
    "professional": "clean, corporate, polished, high-quality photography style",
    "vibrant":       "vibrant colors, energetic, eye-catching, modern design",
    "minimalist":    "minimalist, white space, simple, elegant, flat design",
    "warm":          "warm tones, friendly, approachable, lifestyle photography",
    "bold":          "bold typography, strong contrast, impactful, graphic design style",
}

PLATFORM_GUIDANCE = {
    "facebook":  "suitable for Facebook feed, square format, clear focal point",
    "instagram": "Instagram-worthy, aesthetically pleasing, square format",
    "linkedin":  "professional business image, landscape format, corporate style",
    "twitter":   "attention-grabbing, landscape format, clear messaging",
    "tiktok":    "trendy, vertical format, bold, youth-oriented, high energy",
}


def get_active_image_model() -> tuple[Optional[str], Optional[str]]:
    """
    Return (model_id, provider) for the globally configured best image model.
    Falls back: FLUX Pro → DALL-E 3 → error.
    """
    config = db.get_model_config("image", "best")
    if config and config.get("model_id"):
        model_id = config["model_id"]
        provider = config["provider"]
    else:
        # Auto-select based on available API keys
        if os.environ.get("FAL_API_KEY"):
            model_id, provider = "fal-ai/flux-pro", "fal"
        elif os.environ.get("OPENAI_API_KEY"):
            model_id, provider = "dall-e-3", "openai"
        else:
            return None, None

    # Validate key is actually present
    if provider == "fal" and not os.environ.get("FAL_API_KEY"):
        if os.environ.get("OPENAI_API_KEY"):
            return "dall-e-3", "openai"
        return None, None
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        return None, None
    if provider == "google" and not os.environ.get("GEMINI_API_KEY"):
        return None, None

    return model_id, provider


def generate_image(prompt: str, platform: str = "facebook",
                   business_name: str = "", style: str = "professional") -> dict:
    """
    Generate an image using the globally configured best model.
    All paying tiers use the same top model — limits are enforced by billing, not model quality.
    Raises ValueError if no image API key is configured.
    """
    model_id, provider = get_active_image_model()

    if not model_id:
        raise ValueError(
            "No image generation API key configured. "
            "Add your FAL_API_KEY (recommended) or OPENAI_API_KEY in Settings → API Keys."
        )

    full_prompt = _build_image_prompt(prompt, business_name, style, platform)
    result = None

    if provider == "openai":
        return _generate_dalle(full_prompt, platform, model_id)
    elif provider == "fal":
        return _generate_fal(full_prompt, platform, model_id)
    elif provider == "google":
        return _generate_imagen(full_prompt, platform, model_id)
    else:
        raise ValueError(f"Unknown image provider: {provider}")


# ── Provider implementations ───────────────────────────────────────────────────

def _generate_dalle(prompt: str, platform: str, model_id: str = "dall-e-3") -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    size    = DALLE_PLATFORM_SIZES.get(platform, "1024x1024")
    quality = "hd" if platform == "linkedin" else "standard"
    response = client.images.generate(
        model=model_id,
        prompt=prompt[:4000],
        size=size,
        quality=quality,
        n=1,
        response_format="b64_json",
    )
    item = response.data[0]
    return {
        "b64_json":       item.b64_json,
        "revised_prompt": getattr(item, "revised_prompt", prompt),
        "model":          model_id,
        "provider":       "openai",
        "platform":       platform,
    }


def _generate_fal(prompt: str, platform: str, model_id: str) -> dict:
    from saas.model_registry import generate_image_fal
    result = generate_image_fal(prompt[:1000], model_id, platform)
    return {
        "b64_json": result["b64_json"],
        "revised_prompt": prompt,
        "model":    model_id,
        "provider": "fal",
        "platform": platform,
    }


def _generate_imagen(prompt: str, platform: str, model_id: str) -> dict:
    """Generate via Google Imagen 3 (Vertex AI)."""
    import requests as req
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY not set.")
    r = req.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict",
        params={"key": key},
        json={"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1}},
        timeout=60,
    )
    if not r.ok:
        raise ValueError(f"Imagen error: {r.text[:200]}")
    predictions = r.json().get("predictions", [])
    if not predictions:
        raise ValueError("Imagen returned no images.")
    b64 = predictions[0].get("bytesBase64Encoded", "")
    return {
        "b64_json": b64,
        "revised_prompt": prompt,
        "model":    model_id,
        "provider": "google",
        "platform": platform,
    }


# ── Utilities ──────────────────────────────────────────────────────────────────

def save_b64_image(b64_data: str, path: str) -> str:
    """Save base64 image data to disk. Returns the file path."""
    img_bytes = base64.b64decode(b64_data)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def _build_image_prompt(user_prompt: str, business_name: str,
                         style: str, platform: str) -> str:
    biz_context = f"for {business_name} " if business_name else ""
    style_desc  = STYLE_MAP.get(style, STYLE_MAP["professional"])
    plat_desc   = PLATFORM_GUIDANCE.get(platform, "")
    return (
        f"Create a {style_desc} social media image {biz_context}"
        f"about: {user_prompt}. "
        f"Style: {plat_desc}. "
        f"No text or typography in the image. "
        f"Photorealistic, commercial quality, high resolution."
    )
