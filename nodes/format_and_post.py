# nodes/format_and_post.py
from state import SocialMediaState

from formatters.twitter   import format_for_twitter
from formatters.instagram import format_for_instagram
from formatters.linkedin  import format_for_linkedin
from formatters.facebook  import format_for_facebook

FORMATTERS = {
    "twitter":   format_for_twitter,
    "instagram": format_for_instagram,
    "linkedin":  format_for_linkedin,
    "facebook":  format_for_facebook,
}


def format_and_post(state: SocialMediaState) -> dict:
    platform = state["current_platform"]

    print(f"\n{'='*40}")
    print(f"[*] Processing: {platform.upper()}")
    print(f"{'='*40}")

    try:
        formatted = FORMATTERS[platform](state)
        caption   = formatted["caption"]
        
        # We try to resolve the image, but we catch specific "limit over" errors 
        # so the caption still gets to the review screen.
        try:
            image_result = formatted["image_result"]
            image_mode   = image_result["mode"]
        except Exception as e:
            print(f"❌ {platform} image error: {str(e)}")
            image_mode   = "error"
            image_result = {"mode": "error", "error": str(e)}

        # ── Both mode: store candidates, post AFTER review ────
        if image_mode == "both":
            print(f"📋 {platform}: two image options — user will choose at review")

            return {
                "formatted_posts": {platform: caption},
                "image_candidates": {
                    platform: {
                        "generated": image_result.get("generated"),
                        "uploaded":  image_result.get("uploaded"),
                        "caption":   caption
                    }
                },
                "platform_results": {
                    platform: {"status": "pending_image_choice"}
                },
                "errors": []
            }

        # -- Single image or no image: store for review, post AFTER ----
        else:
            image_path = image_result.get("image_path")
            
            # If there was an error during generation, we track it here
            error_val = image_result.get("error") if image_mode == "error" else None
            
            status_desc = "error" if error_val else ("with image" if image_path else "text only")
            print(f"[*] {platform} ({status_desc}) - ready for review")

            return {
                "formatted_posts": {platform: caption},
                "platform_results": {
                    platform: {
                        "status":     "pending_publish",
                        "image_path": image_path,
                        "caption":    caption,
                        "error":      error_val  # ✅ propagate error to UI
                    }
                },
                "errors": [f"{platform}: {error_val}"] if error_val else []
            }

    except Exception as e:
        error_msg = f"{platform}: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "platform_results": {
                platform: {"status": "failed", "error": str(e)}
            },
            "errors": [error_msg]
        }