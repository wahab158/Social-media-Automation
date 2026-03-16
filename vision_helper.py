import os
from groq import Groq
from sqlite_helper import get_api_key as sqlite_get_key

def analyze_image_with_vision(image_url: str, user_id: str = None) -> str:
    """
    Sends an image URL to Groq's Vision model to get a detailed description
    and extract potential trending keywords for social media generation.
    """
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "groq", "api_key")
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return "No Vision API key available."
        
    client = Groq(api_key=api_key)
    
    prompt = (
        "You are an expert OCR and Image Analysis AI. Analyze this image with extreme precision and return ONLY a JSON object. "
        "1. EXTRACT ALL TEXT: Read every word visible in the image. Focus on Business/Academy names, Course titles, Contact numbers, Locations, and Dates. "
        "2. DESCRIBE VISUALS: Provide a factual description of the imagery and layout. "
        "3. CONFIDENCE: Provide a confidence score (0-100) for your text extraction. "
        "4. UNCERTAINTY: Explicitly list any text that is blurry, partially hidden, or if you are guessing. "
        "\nFormat your response as a raw JSON object with these keys: "
        "\"extracted_text\", \"business_name\", \"contact_info\", \"visual_description\", \"confidence_score\", \"uncertainty_notes\"."
    )
    
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
            timeout=30.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in Vision AI: {e}")
        return f"Could not analyze image. Error: {str(e)}"


# ---------- Platform Ratio Intelligence ----------

PLATFORM_SPECS = {
    "instagram_square":   {"width": 1080, "height": 1080, "ratio": "1:1",    "label": "Instagram Square",   "platform": "instagram"},
    "instagram_portrait": {"width": 1080, "height": 1350, "ratio": "4:5",    "label": "Instagram Portrait", "platform": "instagram"},
    "instagram_story":    {"width": 1080, "height": 1920, "ratio": "9:16",   "label": "Instagram Story",    "platform": "instagram"},
    "facebook_landscape": {"width": 1200, "height": 630,  "ratio": "1.91:1", "label": "Facebook Post",      "platform": "facebook"},
    "linkedin_landscape": {"width": 1200, "height": 627,  "ratio": "1.91:1", "label": "LinkedIn Post",      "platform": "linkedin"},
    "twitter_landscape":  {"width": 1600, "height": 900,  "ratio": "16:9",   "label": "X / Twitter Post",   "platform": "twitter"},
}


def recommend_ratios(image_url: str, user_id: str = None) -> dict:
    """
    Analyzes image content via Groq Vision and recommends the best crop ratio
    per platform using content-aware scoring.
    Returns a dict with recommended ratio key, label, reason, and confidence per platform.
    """
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "groq", "api_key")
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return _fallback_recommendations()

    client = Groq(api_key=api_key)

    analysis_prompt = (
        "Analyze this image and return a JSON object with the following boolean fields: "
        "has_faces, has_person, is_landscape_scene, is_product, is_text_heavy. "
        "Also include a 'labels' array of 5-10 descriptive keywords. "
        "Only return the raw JSON, no markdown fences."
    )

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=300,
            timeout=30.0,
        )
        import json
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        analysis = json.loads(raw)
        return _score_ratios(analysis)
    except Exception as e:
        print(f"Ratio recommendation error: {e}")
        return _fallback_recommendations()


def _score_ratios(analysis: dict) -> dict:
    """
    Applies scoring rules based on image content analysis.
    Higher confidence = better fit for that crop ratio.
    """
    has_faces = analysis.get("has_faces", False)
    has_person = analysis.get("has_person", False)
    is_landscape = analysis.get("is_landscape_scene", False)
    is_product = analysis.get("is_product", False)
    is_text_heavy = analysis.get("is_text_heavy", False)

    recommendations = {}

    # --- Instagram ---
    if has_faces or has_person:
        recommendations["instagram"] = {
            "ratio": "instagram_portrait",
            "label": "4:5 Portrait",
            "reason": "Portrait ratio maximizes screen space for faces and people.",
            "confidence": "High",
        }
    elif is_product:
        recommendations["instagram"] = {
            "ratio": "instagram_square",
            "label": "1:1 Square",
            "reason": "Square format centers products cleanly in the feed.",
            "confidence": "High",
        }
    else:
        recommendations["instagram"] = {
            "ratio": "instagram_square",
            "label": "1:1 Square",
            "reason": "Square is the safe default for mixed content.",
            "confidence": "Medium",
        }

    # --- Facebook ---
    if is_landscape or is_text_heavy:
        recommendations["facebook"] = {
            "ratio": "facebook_landscape",
            "label": "1.91:1 Landscape",
            "reason": "Landscape fills the full Facebook feed card width.",
            "confidence": "High",
        }
    else:
        recommendations["facebook"] = {
            "ratio": "facebook_landscape",
            "label": "1.91:1 Landscape",
            "reason": "Facebook's feed is optimized for wide format images.",
            "confidence": "Medium",
        }

    # --- LinkedIn ---
    recommendations["linkedin"] = {
        "ratio": "linkedin_landscape",
        "label": "1.91:1 Landscape",
        "reason": "LinkedIn feed renders landscape images at full width.",
        "confidence": "High",
    }

    # --- Twitter / X ---
    recommendations["twitter"] = {
        "ratio": "twitter_landscape",
        "label": "16:9 Landscape",
        "reason": "16:9 fills the tweet card and auto-expands in timeline.",
        "confidence": "High",
    }

    return recommendations


def _fallback_recommendations() -> dict:
    """Returns safe defaults when Vision analysis is unavailable."""
    return {
        "instagram": {"ratio": "instagram_square", "label": "1:1 Square", "reason": "Default safe ratio.", "confidence": "Low"},
        "facebook":  {"ratio": "facebook_landscape", "label": "1.91:1 Landscape", "reason": "Default safe ratio.", "confidence": "Low"},
        "linkedin":  {"ratio": "linkedin_landscape", "label": "1.91:1 Landscape", "reason": "Default safe ratio.", "confidence": "Low"},
        "twitter":   {"ratio": "twitter_landscape", "label": "16:9 Landscape", "reason": "Default safe ratio.", "confidence": "Low"},
    }
