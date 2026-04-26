# tools/image_handler.py
import os
from tools.image_generator        import generate_image
from tools.image_prompt_generator import generate_image_prompt

def resolve_image(platform: str, state: dict) -> dict:
    """
    Central image resolver.
    Returns a dict describing what images are available:

    Text only:
    {"mode": "none", "image_path": None}

    Single image (generate or upload):
    {"mode": "single", "image_path": "path/to/image.png"}

    Both options (user picks during review):
    {
        "mode":      "both",
        "generated": "path/to/generated.png",
        "uploaded":  "path/to/uploaded.png"
    }
    """

    image_settings    = state.get("image_settings", {})
    platform_settings = image_settings.get(platform, {})
    mode              = platform_settings.get("mode", "none")

    print(f"[*] {platform} image mode: {mode}")

    # ── No image ──────────────────────────────────────
    if mode == "none":
        return {
            "mode":       "none",
            "image_path": None
        }

    # ── Upload only ───────────────────────────────────
    elif mode == "upload":
        path = platform_settings.get("uploaded_path")

        if not path or not os.path.exists(path):
            print(f"[WARN] Upload path invalid for {platform} -> text only")
            return {"mode": "none", "image_path": None}

        print(f"   -> Using uploaded: {path}")
        return {
            "mode":       "single",
            "image_path": path
        }

    # ── Generate only ─────────────────────────────────
    elif mode == "generate":
        style         = platform_settings.get("style", "realistic")
        image_prompt  = generate_image_prompt(state, style=style, platform=platform)
        generated     = generate_image(prompt=image_prompt, style=style, platform=platform)

        print(f"   -> Generated: {generated}")
        return {
            "mode":       "single",
            "image_path": generated
        }

    # ── Both — generate AND upload ────────────────────
    elif mode == "both":
        result = {"mode": "both"}

        # Generate AI image
        style        = platform_settings.get("style", "realistic")
        image_prompt = generate_image_prompt(state, style=style, platform=platform)
        generated    = generate_image(prompt=image_prompt, style=style, platform=platform)
        result["generated"] = generated
        print(f"   -> Generated: {generated}")

        # Use uploaded image
        uploaded = platform_settings.get("uploaded_path")
        if uploaded and os.path.exists(uploaded):
            result["uploaded"] = uploaded
            print(f"   -> Uploaded: {uploaded}")
        else:
            print(f"[WARN] No valid upload for {platform} in 'both' mode")
            # Fall back to generated only
            return {
                "mode":       "single",
                "image_path": generated
            }

        return result

    else:
        print(f"⚠️  Unknown mode '{mode}' → text only")
        return {"mode": "none", "image_path": None}