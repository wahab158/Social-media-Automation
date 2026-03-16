import os
import cloudinary
from cloudinary import uploader, api
from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

class CloudinaryHelper:
    def list_assets(self, folder=None):
        """Lists assets from Cloudinary (images and videos)."""
        try:
            assets = []
            # We need to call for both images and videos as they are different resource types
            for r_type in ["image", "video"]:
                params = {"resource_type": r_type, "type": "upload", "max_results": 50}
                if folder:
                    params["prefix"] = folder
                
                result = api.resources(**params)
                
                for res in result.get('resources', []):
                    assets.append({
                        "id": res['public_id'],
                        "name": res['public_id'].split('/')[-1],
                        "url": res['secure_url'],
                        "format": res['format'],
                        "resource_type": res['resource_type'],
                        "created_at": res['created_at']
                    })
            
            # Sort by creation date descending
            assets.sort(key=lambda x: x['created_at'], reverse=True)
            return assets
        except Exception as e:
            print(f"Cloudinary List Error: {e}")
            return []

    def upload_asset(self, file_source, folder="social_media_automation"):
        """
        Uploads an asset to Cloudinary.
        file_source: can be a file path, a file-like object, or a URL.
        """
        try:
            result = uploader.upload(
                file_source,
                folder=folder,
                resource_type="auto" # Auto-detect image/video
            )
            return {
                "success": True,
                "public_id": result['public_id'],
                "url": result['secure_url'],
                "resource_type": result['resource_type']
            }
        except Exception as e:
            print(f"Cloudinary Upload Error: {e}")
            return {"success": False, "error": str(e)}

    def get_optimized_url(self, public_id):
        """Generates an optimized delivery URL."""
        url, options = cloudinary_url(public_id, fetch_format="auto", quality="auto")
        return url

    def delete_asset(self, public_id):
        """Deletes an asset from Cloudinary."""
        try:
            result = api.delete_resources([public_id], resource_type="image")
            # If not found in images, try video
            if result.get("deleted", {}).get(public_id) == "not_found":
                result = api.delete_resources([public_id], resource_type="video")
            return {"success": True, "result": result}
        except Exception as e:
            print(f"Cloudinary Delete Error: {e}")
            return {"success": False, "error": str(e)}

# ---------- Platform Transform Intelligence ----------

PLATFORM_SPECS = {
    "instagram_square":   {"width": 1080, "height": 1080},
    "instagram_portrait": {"width": 1080, "height": 1350},
    "instagram_story":    {"width": 1080, "height": 1920},
    "facebook_landscape": {"width": 1200, "height": 630},
    "linkedin_landscape": {"width": 1200, "height": 627},
    "twitter_landscape":  {"width": 1600, "height": 900},
}


def generate_platform_transforms(public_id: str) -> dict:
    """
    Generates Cloudinary transformation URLs for every platform ratio.
    Uses auto:subject gravity so Cloudinary detects and centers
    the main subject automatically.
    Returns a dict of ratio_key -> transformed URL.
    """
    transform_urls = {}
    for key, spec in PLATFORM_SPECS.items():
        url = cloudinary.CloudinaryImage(public_id).build_url(
            width=spec["width"],
            height=spec["height"],
            crop="fill",
            gravity="auto:subject",
            quality="auto:best",
            fetch_format="auto",
        )
        transform_urls[key] = url
    return transform_urls


def generate_single_transform(public_id: str, ratio_key: str) -> str:
    """
    Generates a single transformation URL for a specific ratio.
    Called when user overrides the AI recommendation.
    """
    spec = PLATFORM_SPECS.get(ratio_key)
    if not spec:
        raise ValueError(f"Unknown ratio key: {ratio_key}")
    return cloudinary.CloudinaryImage(public_id).build_url(
        width=spec["width"],
        height=spec["height"],
        crop="fill",
        gravity="auto:subject",
        quality="auto:best",
        fetch_format="auto",
    )


if __name__ == "__main__":
    helper = CloudinaryHelper()
    assets = helper.list_assets()
    print(f"Found {len(assets)} assets on Cloudinary.")
    for a in assets:
        print(f"- {a['name']}: {a['url']}")
