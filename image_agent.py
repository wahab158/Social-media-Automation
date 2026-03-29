import os
import httpx
import json
import asyncio
from typing import Dict, Any
from cloudinary_helper import CloudinaryHelper, generate_platform_batch
from vision_helper import analyze_image_with_vision

STYLE_LIBRARY = {
    "academy": "bold Bauhaus-inspired editorial flat design, geometric shapes, strong typography hierarchy, clean whitespace, inspirational mood",
    "tech_news": "futuristic minimal isometric illustration, abstract data visualization, cool blue and purple tones, precision aesthetic",
    "business": "luxury editorial, high contrast professional photography style, cinematic composition, authoritative executive aesthetic",
    "general": "warm vibrant lifestyle, authentic human energy, candid-style composition, approachable friendly mood"
}

QUALITY_TAGS = "professional graphic design, studio quality, sharp details, no text, no watermarks, social media ready, high resolution, NOT: clipart, stock photo feel, generic AI aesthetic, busy background"

class ImageAgent:
    def __init__(self):
        self.cl_helper = CloudinaryHelper()

    async def generate_pollinations_image(self, prompt: str) -> str:
        """Generates an image using Pollinations.ai (free)."""
        # Encode prompt
        encoded_prompt = httpx.utils.quote(prompt)
        url = f"https://pollinations.ai/p/{encoded_prompt}"
        
        # We can just use the URL as a download source for Cloudinary
        return url

    async def process_post_image(self, topic: str, category: str, brand_profile: dict) -> Dict[str, str]:
        """
        Full Phase 2 Pipeline:
        1. Build Prompt
        2. Generate Image
        3. Upload & Analyze
        4. Apply Brand Overlays
        """
        # 1. Build Prompt
        style = STYLE_LIBRARY.get(category.lower(), STYLE_LIBRARY["general"])
        # Inject brand primary color name if available (simple hex to color mapping or just mention it)
        brand_color_desc = f"Use {brand_profile.get('primary_color', 'blue')} as primary brand color."
        full_prompt = f"{topic}. {style}. {brand_color_desc} {QUALITY_TAGS}"
        
        # 2. Generate Image (Proxy URL)
        img_url = await self.generate_pollinations_image(full_prompt)
        
        # 3. Upload to Cloudinary
        upload_res = self.cl_helper.upload_asset(img_url, folder=f"brand_{brand_profile.get('id')}")
        if not upload_res["success"]:
            raise Exception(f"Cloudinary upload failed: {upload_res.get('error')}")
        
        public_id = upload_res["public_id"]
        secure_url = upload_res["url"]
        
        # 4. Analyze Brightness with Groq Vision
        vision_res_raw = analyze_image_with_vision(secure_url)
        # Simple heuristic: look for 'dark' or 'light' in vision response
        logo_variant = "logo_light" # fallback
        if "dark background" in vision_res_raw.lower() or "dark theme" in vision_res_raw.lower():
            logo_variant = brand_profile.get("logo_light_url") # Light logo on dark BG
        else:
            logo_variant = brand_profile.get("logo_dark_url")  # Dark logo on light BG
        
        # Extract Cloudinary Public ID from the logo URL (heuristic)
        logo_public_id = None
        if logo_variant and "res.cloudinary.com" in logo_variant:
            # e.g. https://res.cloudinary.com/cloud/image/upload/v1/folder/logo_id.png
            parts = logo_variant.split('/')
            filename = parts[-1].split('.')[0]
            # If there's a folder, it's harder, but let's assume simple layout for now
            # Best is to store the public_id in the brand_profiles table
            # For now, we take from parts
            logo_public_id = filename 

        # 5. Generate Multi-Platform Batch
        brand_settings = {
            "logo_id": logo_public_id,
            "primary_color": brand_profile.get("primary_color"),
            "contact_text": f"{brand_profile.get('name')} | {brand_profile.get('website', '')}"
        }
        
        crops = generate_platform_batch(public_id, brand_settings)
        return {
            "original_url": secure_url,
            "public_id": public_id,
            "crops": crops
        }

if __name__ == "__main__":
    # Test stub
    agent = ImageAgent()
    async def test():
        res = await agent.process_post_image("AI breakthrough", "tech_news", {"id": "test", "name": "AI Lab", "primary_color": "#00CCFF"})
        print(json.dumps(res, indent=2))
    # asyncio.run(test())
