import os
import requests
from dotenv import load_dotenv

load_dotenv()

def post_to_linkedin(content: str) -> dict:
    """
    Posts text content to LinkedIn.
    Uses UGC Posts API (User Generated Content).
    """

    # ── Mock Mode ─────────────────────────────────────
    if os.getenv("MOCK_POSTING", "false").lower() == "true":
        return _mock_post("linkedin", content)

    # ── Real Posting ──────────────────────────────────
    _validate_linkedin_keys()

    try:
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        person_id    = os.getenv("LINKEDIN_PERSON_ID")

        url     = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        payload = {
            "author":         f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        result   = response.json()

        if response.status_code not in [200, 201]:
            raise Exception(
                f"LinkedIn API error {response.status_code}: "
                f"{result.get('message', result)}"
            )

        post_id = result.get("id", "").split(":")[-1]
        url     = f"https://www.linkedin.com/feed/update/{result.get('id')}"

        print(f"[OK] LinkedIn post live: {url}")

        return {
            "status":   "success",
            "post_id":  post_id,
            "url":      url,
            "platform": "linkedin"
        }

    except Exception as e:
        return {
            "status":   "failed",
            "error":    _handle_linkedin_error(str(e)),
            "platform": "linkedin"
        }


def _handle_linkedin_error(error: str) -> str:
    """Converts LinkedIn errors into readable messages."""

    if "401" in error:
        return (
            "LinkedIn authentication failed. "
            "Your access token may have expired. "
            "LinkedIn tokens expire every 60 days."
        )
    elif "403" in error:
        return (
            "LinkedIn permission error. "
            "Make sure your app has w_member_social permission."
        )
    elif "422" in error:
        return (
            "LinkedIn rejected the post content. "
            "Check for special characters or invalid formatting."
        )
    else:
        return f"LinkedIn error: {error}"


def _validate_linkedin_keys():
    required = [
        "LINKEDIN_ACCESS_TOKEN",
        "LINKEDIN_PERSON_ID",
    ]

    missing = [k for k in required if not os.getenv(k)]

    if missing:
        raise EnvironmentError(
            f"\n❌ Missing LinkedIn keys: {missing}"
            f"\n👉 Add them to your .env file"
            f"\n🔗 Get keys at: https://www.linkedin.com/developers"
        )


def _mock_post(platform: str, content: str) -> dict:
    print(f"[MOCK] MOCK MODE - simulating {platform} post")
    print(f"   Content preview: {content[:80]}...")

    return {
        "status":   "success",
        "post_id":  f"mock_{platform}_12345",
        "url":      f"https://{platform}.com/mock/post/12345",
        "platform": platform,
        "mock":     True
    }