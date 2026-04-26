# nodes/router.py
from langgraph.constants import Send
from state import SocialMediaState

def platform_router(state: SocialMediaState):
    # ✅ Safe access — prevents KeyError on revision loop
    platforms = state.get("target_platforms", [])
    mode      = state.get("posting_mode", "simultaneous")

    print(f"[*] Routing to: {platforms} ({mode} mode)")

    # [OK] Safety check - no platforms selected
    if not platforms:
        print("[WARN] No platforms selected - nothing to post")
        return []

    if mode == "simultaneous":
        # Fan-out: all platforms run in parallel
        return [
            Send("format_and_post", {**state, "current_platform": p})
            for p in platforms
        ]

    elif mode == "single":
        # Only post to the first platform in the list
        return [
            Send("format_and_post", {**state, "current_platform": platforms[0]})
        ]

    # ✅ Unknown mode fallback — treat as simultaneous
    else:
        print(f"⚠️  Unknown posting mode '{mode}' — defaulting to simultaneous")
        return [
            Send("format_and_post", {**state, "current_platform": p})
            for p in platforms
        ]