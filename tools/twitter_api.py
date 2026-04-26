# tools/twitter_api.py
import os
import tweepy
from dotenv import load_dotenv

load_dotenv()


def post_to_twitter(content: dict) -> dict:
    """
    Posts text + optional image to Twitter/X.
    Accepts a dict with 'caption' and 'image_path'.
    Uses mock mode if MOCK_POSTING=true in .env
    """

    # ✅ Extract caption and image from dict
    caption    = content.get("caption",    "")
    image_path = content.get("image_path", None)

    # ── Mock Mode ─────────────────────────────────────
    if os.getenv("MOCK_POSTING", "false").lower() == "true":
        return _mock_post("twitter", caption, image_path)

    # ── Real Posting ──────────────────────────────────
    _validate_twitter_keys()

    try:
        # -- Truncate if too long ----------------------
        if len(caption) > 280:
            print(f"[WARN] Tweet too long ({len(caption)} chars) - truncating")
            caption = caption[:277] + "..."

        # -- Upload image if provided ------------------
        media_id = None

        if image_path and os.path.exists(image_path):
            print(f"[UPLOAD] Uploading image to Twitter: {image_path}")

            # Image upload requires v1.1 API
            auth = tweepy.OAuth1UserHandler(
                consumer_key=       os.getenv("TWITTER_API_KEY"),
                consumer_secret=    os.getenv("TWITTER_API_SECRET"),
                access_token=       os.getenv("TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
            )
            api_v1  = tweepy.API(auth)
            media   = api_v1.media_upload(filename=image_path)
            media_id = media.media_id_string
            print(f"[OK] Image uploaded - media_id: {media_id}")

        elif image_path:
            print(f"[WARN] Image path not found: {image_path} - posting text only")

        # ── Post tweet ────────────────────────────────
        client = tweepy.Client(
            bearer_token=        os.getenv("TWITTER_BEARER_TOKEN"),
            consumer_key=        os.getenv("TWITTER_API_KEY"),
            consumer_secret=     os.getenv("TWITTER_API_SECRET"),
            access_token=        os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret= os.getenv("TWITTER_ACCESS_SECRET")
        )

        # Attach media if uploaded
        kwargs = {"text": caption}
        if media_id:
            kwargs["media_ids"] = [media_id]

        response = client.create_tweet(**kwargs)
        tweet_id = response.data["id"]
        url      = f"https://twitter.com/i/web/status/{tweet_id}"

        print(f"[OK] Twitter post live: {url}")

        return {
            "status":    "success",
            "post_id":   tweet_id,
            "url":       url,
            "platform":  "twitter",
            "has_image": media_id is not None
        }

    except tweepy.TweepyException as e:
        error = _handle_twitter_error(e)
        return {
            "status":   "failed",
            "error":    error,
            "platform": "twitter"
        }

    except Exception as e:
        return {
            "status":   "failed",
            "error":    str(e),
            "platform": "twitter"
        }


def _validate_twitter_keys():
    required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"\n❌ Missing Twitter API keys: {missing}"
            f"\n👉 Add them to your .env file"
            f"\n🔗 Get keys at: https://developer.twitter.com"
        )


def _handle_twitter_error(e: tweepy.TweepyException) -> str:
    error_str = str(e)

    if "403" in error_str:
        return (
            "Twitter API permission error. "
            "Check your app has 'Read and Write' permissions "
            "in the Twitter Developer Portal."
        )
    elif "401" in error_str:
        return (
            "Twitter authentication failed. "
            "Check your API keys and tokens are correct."
        )
    elif "429" in error_str:
        return (
            "Twitter rate limit reached. "
            "Too many posts in a short time. Try again later."
        )
    elif "duplicate" in error_str.lower():
        return (
            "Twitter rejected duplicate content. "
            "Change the post text slightly and try again."
        )
    else:
        return f"Twitter error: {error_str}"


def _mock_post(platform: str, caption: str, image_path: str = None) -> dict:
    """Simulates a successful post without calling any API."""

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