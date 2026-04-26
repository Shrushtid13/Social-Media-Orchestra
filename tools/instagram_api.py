import os
import requests
from dotenv import load_dotenv

load_dotenv()

def post_to_instagram(content: dict) -> dict:
    """
    Posts caption + image to Instagram.

    content = {
        "caption":    "post text with hashtags",
        "image_path": "path/to/image.png"
    }

    Instagram posting is a 3 step process:
    1. Upload image to public hosting (Cloudinary)
    2. Create media container on Instagram
    3. Publish the container
    4. Fetch real permalink from Graph API
    """

    caption    = content["caption"]
    image_path = content.get("image_path")

    # ── Mock Mode ─────────────────────────────────────
    if os.getenv("MOCK_POSTING", "false").lower() == "true":
        return _mock_post("instagram", caption)

    # ── Real Posting ──────────────────────────────────
    _validate_instagram_keys()

    try:
        access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        account_id   = os.getenv("INSTAGRAM_ACCOUNT_ID")

        # Step 1: Get public image URL
        if image_path:
            print("☁️  Uploading image to Cloudinary...")
            image_url = _upload_to_cloudinary(image_path)
            print(f"✅ Image uploaded: {image_url}")
        else:
            image_url = None

        # Step 2: Create media container
        print("📦 Creating Instagram media container...")
        container_id = _create_container(
            account_id, access_token, caption, image_url
        )

        # Step 3: Publish container
        print("🚀 Publishing to Instagram...")
        post_id = _publish_container(
            account_id, access_token, container_id
        )

        # Step 4: Fetch real permalink from Graph API
        # (post_id is a numeric ID, NOT the shortcode used in instagram.com/p/)
        print("🔗 Fetching real permalink...")
        url = _fetch_permalink(post_id, access_token)
        print(f"✅ Instagram post live: {url}")

        return {
            "status":   "success",
            "post_id":  post_id,
            "url":      url,
            "platform": "instagram"
        }

    except Exception as e:
        return {
            "status":   "failed",
            "error":    str(e),
            "platform": "instagram"
        }


def _create_container(
    account_id:   str,
    access_token: str,
    caption:      str,
    image_url:    str = None
) -> str:
    """Creates Instagram media container. Returns container ID."""

    url  = f"https://graph.facebook.com/v18.0/{account_id}/media"
    data = {
        "caption":      caption,
        "access_token": access_token
    }

    if image_url:
        data["image_url"]  = image_url
        data["media_type"] = "IMAGE"
    else:
        # Text only post (carousel or reels need different approach)
        data["media_type"] = "IMAGE"

    response = requests.post(url, data=data)
    result   = response.json()

    if "id" not in result:
        raise Exception(
            f"Container creation failed: {result.get('error', result)}"
        )

    return result["id"]


def _publish_container(
    account_id:   str,
    access_token: str,
    container_id: str
) -> str:
    """Publishes Instagram container. Returns post ID."""

    url  = f"https://graph.facebook.com/v18.0/{account_id}/media_publish"
    data = {
        "creation_id":  container_id,
        "access_token": access_token
    }

    response = requests.post(url, data=data)
    result   = response.json()

    if "id" not in result:
        raise Exception(
            f"Publishing failed: {result.get('error', result)}"
        )

    return result["id"]


def _fetch_permalink(post_id: str, access_token: str) -> str:
    """
    Fetches the real public permalink for a published Instagram post.
    The numeric post_id from publish API is NOT the URL shortcode.
    We need to call the Graph API to get instagram.com/p/<shortcode>/
    """

    url    = f"https://graph.facebook.com/v18.0/{post_id}"
    params = {
        "fields":       "permalink",
        "access_token": access_token
    }

    response = requests.get(url, params=params)
    result   = response.json()

    if "permalink" in result:
        return result["permalink"]

    # Fallback: return a generic profile link if permalink unavailable
    print(f"⚠️  Could not fetch permalink: {result}")
    return f"https://www.instagram.com/"


def _upload_to_cloudinary(image_path: str) -> str:
    """
    Uploads local image to Cloudinary.
    Returns public URL that Instagram can access.

    Instagram API cannot read local file paths —
    it needs a publicly accessible URL.
    """

    try:
        import cloudinary
        import cloudinary.uploader

    except ImportError:
        raise ImportError(
            "\n❌ Cloudinary not installed"
            "\n👉 Run: pip install cloudinary"
        )

    _validate_cloudinary_keys()

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=   os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )

    result = cloudinary.uploader.upload(
        image_path,
        folder="social_media_automation"
    )

    return result["secure_url"]


def _validate_instagram_keys():
    required = [
        "INSTAGRAM_ACCESS_TOKEN",
        "INSTAGRAM_ACCOUNT_ID",
    ]

    missing = [k for k in required if not os.getenv(k)]

    if missing:
        raise EnvironmentError(
            f"\n❌ Missing Instagram keys: {missing}"
            f"\n👉 Add them to your .env file"
            f"\n🔗 Get keys at: https://developers.facebook.com"
        )


def _validate_cloudinary_keys():
    required = [
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
    ]

    missing = [k for k in required if not os.getenv(k)]

    if missing:
        raise EnvironmentError(
            f"\n❌ Missing Cloudinary keys: {missing}"
            f"\n👉 Add them to your .env file"
            f"\n🔗 Get free account at: https://cloudinary.com"
        )


def _mock_post(platform: str, content: str) -> dict:
    print(f"🎭 MOCK MODE — simulating {platform} post")
    print(f"   Content preview: {content[:80]}...")

    return {
        "status":   "success",
        "post_id":  f"mock_{platform}_12345",
        "url":      f"https://{platform}.com/mock/post/12345",
        "platform": platform,
        "mock":     True
    }