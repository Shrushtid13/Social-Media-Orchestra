# nodes/aggregator.py
from state import SocialMediaState

def aggregator(state: SocialMediaState) -> dict:
    """
    Final node in the graph.
    Collects all results from parallel platform branches.
    Prints a clean summary of what succeeded and what failed.
    Does not post anything — just reports.
    """

    platform_results = state.get("platform_results", {})
    formatted_posts  = state.get("formatted_posts",  {})
    errors           = state.get("errors",           [])
    chosen_images    = state.get("chosen_images",    {})
    topic            = state.get("topic",            "")

    # ── Separate successes from failures ─────────────
    successes = {
        platform: result
        for platform, result in platform_results.items()
        if result.get("status") == "success"
    }

    failures = {
        platform: result
        for platform, result in platform_results.items()
        if result.get("status") == "failed"
    }

    pending = {
        platform: result
        for platform, result in platform_results.items()
        if result.get("status") == "pending_image_choice"
    }

    # ── Print Summary ─────────────────────────────────
    print("\n")
    print("=" * 50)
    print("[#] POSTING SUMMARY")
    print("=" * 50)

    print("[*] Topic: " + topic[:80])
    print("[*] Total platforms: " + str(len(platform_results)))

    # ── Successes ─────────────────────────────────────
    if successes:
        print("[v] Successfully posted (" + str(len(successes)) + "):")
        for platform, result in successes.items():

            # Get post URL if available
            url      = result.get("url",     "no url")
            post_id  = result.get("post_id", "no id")
            is_mock  = result.get("mock",    False)
            has_image = result.get("has_image", False)

            # Was it posted with an image?
            image_info = ""
            if has_image:
                if platform in chosen_images:
                    image_info = " (chosen image)"
                else:
                    image_info = " (with image)"

            mock_info = " [MOCK]" if is_mock else ""

            print(f"   [PLATFORM] {platform.upper()}{mock_info}{image_info}")
            print(f"      Post ID : {post_id}")
            print(f"      URL     : {url}")

            # Show the formatted post
            caption = formatted_posts.get(platform, "")
            if caption:
                preview = caption[:100] + "..." if len(caption) > 100 else caption
                print(f"      Preview : {preview}")

    # ── Failures ──────────────────────────────────────
    if failures:
        print("[x] Failed (" + str(len(failures)) + "):")
        for platform, result in failures.items():
            error = result.get("error", "unknown error")
            print(f"   [PLATFORM] {platform.upper()}")
            print(f"      Error: {error}")

    # ── Pending (should not happen after publisher) ───
    if pending:
        print(f"\n[PENDING] Still pending ({len(pending)}):")
        for platform in pending:
            print(f"   [PLATFORM] {platform.upper()} - image choice not resolved")

    # ── Errors from state ─────────────────────────────
    if errors:
        print(f"\n[!] Errors collected during run:")
        for error in errors:
            print(f"   -> {error}")

    # ── Final verdict ─────────────────────────────────
    print("\n" + "-" * 50)

    total    = len(platform_results)
    success  = len(successes)
    failed   = len(failures)

    if failed == 0 and total > 0:
        print(f"[SUCCESS] All {total} platform(s) posted successfully!")

    elif success == 0:
        print(f"[FAILED] All {total} platform(s) failed to post.")

    else:
        print(
            f"[WARN] {success}/{total} platforms succeeded, "
            f"{failed} failed."
        )

    print("=" * 50)
    print()

    # ── Return summary dict ───────────────────────────
    # This gets stored in final state
    # Useful for FastAPI to return to React
    return {
        "aggregator_summary": {
            "total":     total,
            "succeeded": success,
            "failed":    failed,
            "successes": {
                p: {
                    "post_id": r.get("post_id"),
                    "url":     r.get("url"),
                    "mock":    r.get("mock", False)
                }
                for p, r in successes.items()
            },
            "failures": {
                p: r.get("error")
                for p, r in failures.items()
            }
        }
    }