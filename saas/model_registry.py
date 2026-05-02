"""
AI Model Registry — curated catalog of text & image generation models.
Supports live fetching of available models from provider APIs.
Admin can assign any model to any subscription tier.
"""
import os, requests
from typing import Optional

# ── Curated model catalog ──────────────────────────────────────────────────────

TEXT_MODELS = [
    {
        "id": "gemini-2.0-flash",
        "provider": "google",
        "name": "Gemini 2.0 Flash",
        "description": "Fast & cheap. Great for most social posts.",
        "cost_note": "~$0.0001/post",
        "quality": "Good",
        "speed": "Fast",
        "recommended_for": ["free", "starter"],
    },
    {
        "id": "gemini-2.5-pro-preview-05-06",
        "provider": "google",
        "name": "Gemini 2.5 Pro",
        "description": "Best quality Gemini. Deeper, more creative posts.",
        "cost_note": "~$0.001/post",
        "quality": "Excellent",
        "speed": "Medium",
        "recommended_for": ["growth", "agency"],
    },
    {
        "id": "gpt-4o",
        "provider": "openai",
        "name": "GPT-4o",
        "description": "OpenAI's flagship. Exceptional writing quality.",
        "cost_note": "~$0.005/post",
        "quality": "Excellent",
        "speed": "Medium",
        "recommended_for": ["agency"],
    },
    {
        "id": "gpt-4o-mini",
        "provider": "openai",
        "name": "GPT-4o Mini",
        "description": "Cheaper OpenAI model. Good balance of cost and quality.",
        "cost_note": "~$0.0003/post",
        "quality": "Good",
        "speed": "Fast",
        "recommended_for": ["starter", "growth"],
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "provider": "anthropic",
        "name": "Claude 3.5 Haiku",
        "description": "Anthropic's fastest model. Crisp, clear copy.",
        "cost_note": "~$0.0002/post",
        "quality": "Very Good",
        "speed": "Fast",
        "recommended_for": ["starter", "growth"],
    },
    {
        "id": "claude-3-7-sonnet-20250219",
        "provider": "anthropic",
        "name": "Claude 3.7 Sonnet",
        "description": "Anthropic's best model. Outstanding creative writing.",
        "cost_note": "~$0.003/post",
        "quality": "Excellent",
        "speed": "Medium",
        "recommended_for": ["growth", "agency"],
    },
]

IMAGE_MODELS = [
    {
        "id": "fal-ai/flux/schnell",
        "provider": "fal",
        "name": "FLUX Schnell",
        "description": "Ultra-fast. 4 steps. Great for quick previews.",
        "cost_note": "~$0.003/image",
        "quality": "Good",
        "speed": "Very Fast",
        "recommended_for": ["starter"],
    },
    {
        "id": "fal-ai/flux/dev",
        "provider": "fal",
        "name": "FLUX Dev",
        "description": "High quality open-weight model. Excellent realism.",
        "cost_note": "~$0.025/image",
        "quality": "Very Good",
        "speed": "Medium",
        "recommended_for": ["growth"],
    },
    {
        "id": "fal-ai/flux-pro",
        "provider": "fal",
        "name": "FLUX Pro",
        "description": "Best-in-class photorealism. Top choice for social media.",
        "cost_note": "~$0.055/image",
        "quality": "Excellent",
        "speed": "Medium",
        "recommended_for": ["agency"],
    },
    {
        "id": "fal-ai/flux-pro/v1.1-ultra",
        "provider": "fal",
        "name": "FLUX Pro 1.1 Ultra",
        "description": "Latest FLUX. Up to 4MP output. Stunning detail.",
        "cost_note": "~$0.06/image",
        "quality": "Best",
        "speed": "Slow",
        "recommended_for": ["agency"],
    },
    {
        "id": "dall-e-3",
        "provider": "openai",
        "name": "DALL-E 3",
        "description": "OpenAI's image model. Great prompt adherence.",
        "cost_note": "~$0.04/image",
        "quality": "Good",
        "speed": "Medium",
        "recommended_for": ["growth"],
    },
    {
        "id": "fal-ai/ideogram/v2",
        "provider": "fal",
        "name": "Ideogram v2",
        "description": "Best for text in images. Logos, banners, posters.",
        "cost_note": "~$0.08/image",
        "quality": "Excellent (text)",
        "speed": "Medium",
        "recommended_for": ["growth", "agency"],
    },
    {
        "id": "fal-ai/stable-diffusion-v35-large",
        "provider": "fal",
        "name": "Stable Diffusion 3.5 Large",
        "description": "Open-source SD. Great artistic styles.",
        "cost_note": "~$0.04/image",
        "quality": "Very Good",
        "speed": "Medium",
        "recommended_for": ["starter", "growth"],
    },
]

# Default model assignment per tier
DEFAULT_TEXT_CONFIGS = {
    "free":    "gemini-2.0-flash",
    "starter": "gemini-2.0-flash",
    "growth":  "gemini-2.5-pro-preview-05-06",
    "agency":  "gemini-2.5-pro-preview-05-06",
}

DEFAULT_IMAGE_CONFIGS = {
    "free":    None,                        # No image gen on free tier
    "starter": "fal-ai/flux/schnell",
    "growth":  "fal-ai/flux/dev",
    "agency":  "fal-ai/flux-pro",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_text_model(model_id: str) -> Optional[dict]:
    return next((m for m in TEXT_MODELS if m["id"] == model_id), None)

def get_image_model(model_id: str) -> Optional[dict]:
    return next((m for m in IMAGE_MODELS if m["id"] == model_id), None)

def get_provider_for_model(model_id: str, model_type: str) -> Optional[str]:
    catalog = TEXT_MODELS if model_type == "text" else IMAGE_MODELS
    m = next((x for x in catalog if x["id"] == model_id), None)
    return m["provider"] if m else None


# ── Live model fetching from providers ────────────────────────────────────────

def fetch_google_models() -> list[dict]:
    """Fetch available Gemini models from Google AI."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return []
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": key}, timeout=8
        )
        if not r.ok:
            return []
        models = r.json().get("models", [])
        results = []
        for m in models:
            name = m.get("name", "").replace("models/", "")
            if "generateContent" in m.get("supportedGenerationMethods", []):
                results.append({
                    "id": name,
                    "provider": "google",
                    "name": m.get("displayName", name),
                    "description": m.get("description", ""),
                    "cost_note": "Check Google AI pricing",
                    "quality": "—",
                    "speed": "—",
                    "recommended_for": [],
                    "live": True,
                })
        return results
    except Exception:
        return []

def fetch_openai_models() -> list[dict]:
    """Fetch available GPT models from OpenAI."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return []
    try:
        r = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"}, timeout=8
        )
        if not r.ok:
            return []
        models = r.json().get("data", [])
        # Filter to useful text/image models
        relevant = [m for m in models if any(
            x in m["id"] for x in ["gpt-4", "gpt-3.5", "dall-e", "o1", "o3"]
        )]
        return [{
            "id": m["id"],
            "provider": "openai",
            "name": m["id"],
            "description": "OpenAI model",
            "cost_note": "Check OpenAI pricing",
            "quality": "—",
            "speed": "—",
            "recommended_for": [],
            "live": True,
        } for m in relevant]
    except Exception:
        return []

def fetch_all_live_models() -> dict:
    """
    Fetch latest available models from all configured providers.
    Returns {"text": [...], "image": [...]} merging live + curated.
    """
    live_text  = fetch_google_models() + fetch_openai_models()
    # Merge: live models not already in catalog get added
    curated_ids_text  = {m["id"] for m in TEXT_MODELS}
    curated_ids_image = {m["id"] for m in IMAGE_MODELS}

    extra_text = [m for m in live_text if m["id"] not in curated_ids_text]

    return {
        "text":  TEXT_MODELS  + extra_text,
        "image": IMAGE_MODELS,   # fal.ai doesn't have a public list API
        "new_text_count":  len(extra_text),
    }


# ── Image generation via fal.ai ───────────────────────────────────────────────

FAL_SIZES = {
    "instagram": {"width": 1024, "height": 1024},
    "tiktok":    {"width": 768,  "height": 1344},
    "linkedin":  {"width": 1344, "height": 768},
    "facebook":  {"width": 1024, "height": 1024},
    "twitter":   {"width": 1200, "height": 675},
}

def generate_image_fal(prompt: str, model_id: str, platform: str) -> dict:
    """
    Generate an image via fal.ai REST API.
    Returns {"url": "...", "b64_json": None} or raises on failure.
    """
    key = os.environ.get("FAL_API_KEY", "")
    if not key:
        raise ValueError("FAL_API_KEY not set. Add it in Settings → API Keys.")

    size = FAL_SIZES.get(platform, {"width": 1024, "height": 1024})

    # fal.ai uses different param names per model
    payload = {
        "prompt": prompt,
        "image_size": {"width": size["width"], "height": size["height"]},
        "num_images": 1,
    }
    # FLUX models accept num_inference_steps
    if "flux/schnell" in model_id:
        payload["num_inference_steps"] = 4
    elif "flux" in model_id:
        payload["num_inference_steps"] = 28
        payload["guidance_scale"] = 3.5

    # Convert model_id to fal.run URL  e.g. fal-ai/flux/pro → https://fal.run/fal-ai/flux/pro
    url = f"https://fal.run/{model_id}"

    r = requests.post(
        url,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if not r.ok:
        raise ValueError(f"fal.ai error {r.status_code}: {r.text[:200]}")

    data = r.json()
    images = data.get("images", [])
    if not images:
        raise ValueError("fal.ai returned no images.")

    img_url = images[0].get("url", "")
    # Download and return as base64 so we can save locally
    img_r = requests.get(img_url, timeout=30)
    import base64
    b64 = base64.b64encode(img_r.content).decode()
    return {"b64_json": b64, "url": img_url}
