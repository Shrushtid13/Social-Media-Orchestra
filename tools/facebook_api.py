# tools/facebook_api.py
import os
from dotenv import load_dotenv

load_dotenv()

def post_to_facebook(content: dict) -> dict:
    """
    Posts caption + image to Facebook.
    (Mocked for now as per user request to fulfill architecture)
    """

    caption    = content.get("caption", "")
    image_path = content.get("image_path")

    # ── Mock Mode ─────────────────────────────────────
    # Even if not explicitly set to mock, we mock it here because we don't have the API logic yet
    return _mock_post("facebook", caption, image_path)


def _mock_post(platform: str, caption: str, image_path: str = None) -> dict:
    print(f"[MOCK] MOCK MODE - simulating {platform} post")
    print(f"   Caption preview: {caption[:80]}...")
    if image_path:
        print(f"   Image: {image_path}")

    return {
        "status":    "success",
        "post_id":   f"mock_{platform}_12345",
        "url":       f"https://{platform}.com/mock/post/12345",
        "platform":  platform,
        "has_image": image_path is not None,
        "mock":      True
    }
