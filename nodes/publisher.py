# nodes/publisher.py
from state import SocialMediaState

from tools.twitter_api   import post_to_twitter
from tools.instagram_api import post_to_instagram
from tools.linkedin_api  import post_to_linkedin
from tools.facebook_api   import post_to_facebook

POSTERS = {
    "twitter":   post_to_twitter,
    "instagram": post_to_instagram,
    "linkedin":  post_to_linkedin,
    "facebook":  post_to_facebook,
}


def publisher(state: SocialMediaState) -> dict:
    """
    Runs after human approval.
    Posts ALL platforms that are pending_publish or pending_image_choice.

    pending_publish      → normal mode (none/generate/upload)
                           caption + image_path stored in platform_results
    pending_image_choice → "both" mode
                           human picked image stored in chosen_images
    """

    formatted_posts  = state.get("formatted_posts",  {})
    platform_results = state.get("platform_results", {})
    chosen_images    = state.get("chosen_images",    {})
    new_results      = {}

    for platform, current_result in platform_results.items():
        status = current_result.get("status")

        # ── Normal mode: pending_publish ──────────────
        if status == "pending_publish":
            caption    = current_result.get("caption", formatted_posts.get(platform, ""))
            image_path = current_result.get("image_path")

            print(f"[PUBLISH] Publishing {platform}...")

            result = POSTERS[platform]({
                "caption":    caption,
                "image_path": image_path
            })

            status_msg = "[OK]" if result["status"] == "success" else "[X]"
            has_image  = "with image" if image_path else "text only"
            print(f"{status_msg} {platform} ({has_image})")

            new_results[platform] = result

        # ── Both mode: pending_image_choice ───────────
        elif status == "pending_image_choice":
            image_path = chosen_images.get(platform)
            caption    = formatted_posts.get(platform, "")

            if not image_path:
                print(f"[WARN] {platform}: no image chosen - posting text only")

            print(f"[PUBLISH] Publishing {platform} with chosen image...")

            result = POSTERS[platform]({
                "caption":    caption,
                "image_path": image_path
            })

            status_msg = "[OK]" if result["status"] == "success" else "[X]"
            print(f"{status_msg} {platform} published")

            new_results[platform] = result

        # ── Already failed or unknown — skip ──────────
        else:
            print(f"[SKIP] Skipping {platform} (status: {status})")

    return {
        "platform_results": new_results
    }