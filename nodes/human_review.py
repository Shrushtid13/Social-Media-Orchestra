# nodes/human_review.py
from langgraph.types import interrupt
from state import SocialMediaState


def human_review_node(state: SocialMediaState) -> dict:
    """
    Pauses the graph completely using interrupt().
    Waits for human to review posts and make a decision.

    Two responsibilities:
    1. Show formatted posts + image candidates to human
    2. Collect decision: approve / revise / reject
       + image choices for "both" mode platforms

    In terminal (main.py):
        interrupt() pauses → show_review() in main.py
        collects input → Command(resume=decision) resumes

    In Streamlit (app.py):
        interrupt() pauses → Streamlit shows review phase
        user clicks submit → Command(resume=decision) resumes

    In FastAPI (backend/main.py):
        interrupt() pauses → job status = "awaiting_review"
        POST /api/review/{job_id} → Command(resume=decision) resumes
    """

    formatted_posts  = state.get("formatted_posts",  {})
    image_candidates = state.get("image_candidates", {})
    review_count     = state.get("review_count",     0)
    topic            = state.get("topic",            "")

    # ── Build review package ──────────────────────────
    # This is what gets passed to interrupt()
    # In Streamlit and FastAPI, this data is read from
    # graph.get_state(config).values after the pause

    review_package = {

        # Basic info
        "topic":          topic,
        "review_number":  review_count + 1,

        # All formatted posts — one per platform
        # {"twitter": "tweet text", "instagram": "caption", ...}
        "formatted_posts": formatted_posts,

        # Image candidates for "both" mode platforms
        # Empty dict if no platform used "both" mode
        # {
        #   "twitter": {
        #     "generated": "generated_images/abc.png",
        #     "uploaded":  "uploads/twitter_photo.png"
        #   }
        # }
        "image_candidates": image_candidates,

        # Which platforms need image choice from human
        # [] if no platform used "both" mode
        "platforms_needing_image_choice": list(image_candidates.keys()),

        # Instructions shown to human
        "instructions": (
            "1. Review each post carefully\n"
            "2. For platforms with two images, choose one\n"
            "3. Set action to: approve / revise / reject\n"
            "4. If revising, add notes explaining what to change"
        )
    }

    # ── Log what's being reviewed ─────────────────────
    print("\n" + "="*55)
    print("[#] GRAPH PAUSED -- Review Round " + str(review_count + 1))
    print("="*55)

    for platform, caption in formatted_posts.items():
        icons = {
            "twitter":   "[Twitter]",
            "instagram": "[Instagram]",
            "linkedin":  "[LinkedIn]",
            "facebook":  "[Facebook]"
        }
        icon = icons.get(platform, "[Post]")
        print(f"\n{icon}  {platform.upper()}")
        print("-" * 40)
        print(caption[:200] + "..." if len(caption) > 200 else caption)

    if image_candidates:
        print("\n[#] Image choices needed for: " +
              str(list(image_candidates.keys())))

    print("\n[?] Waiting for human decision...")
    print("="*55)

    # ── PAUSE GRAPH ───────────────────────────────────
    # Everything above was setup
    # This single line freezes the entire graph
    # State is saved to MemorySaver checkpointer
    # Graph will not move forward until
    # graph.invoke(Command(resume=decision)) is called

    decision = interrupt(review_package)

    # ── GRAPH RESUMES HERE ────────────────────────────
    # decision comes from Command(resume={...})
    # Structure expected:
    # {
    #   "action":        "approve" | "revise" | "reject",
    #   "notes":         "feedback text if revising",
    #   "image_choices": {"twitter": "generated" | "uploaded"}
    # }

    action        = decision.get("action",        "reject")
    notes         = decision.get("notes",         "")
    image_choices = decision.get("image_choices", {})

    print("[>] Graph resumed -- Decision: " + action)
    if notes:
        print("    Notes: " + notes)
    if image_choices:
        print("    Image choices: " + str(image_choices))

    # ── Validate action ───────────────────────────────
    valid_actions = ["approve", "revise", "reject"]
    if action not in valid_actions:
        print(
            f"[WARN] Invalid action '{action}' - defaulting to reject"
        )
        action = "reject"

    # ── Resolve chosen images ─────────────────────────
    # For each platform that used "both" mode,
    # map the human's choice ("generated"/"uploaded")
    # to the actual file path

    chosen_images = {}

    for platform, choice in image_choices.items():

        if platform not in image_candidates:
            continue

        candidates = image_candidates[platform]

        if choice == "generated":
            chosen_images[platform] = candidates.get("generated")
            print("   [v] " + platform + ": using AI generated image")

        elif choice == "uploaded":
            chosen_images[platform] = candidates.get("uploaded")
            print("   [v] " + platform + ": using uploaded image")

        else:
            # Unknown choice — default to generated
            chosen_images[platform] = candidates.get("generated")
            print(
                "   [!] " + platform + ": unknown choice '" + choice + "' "
                "-- defaulting to generated"
            )

    # ── Return updated state ──────────────────────────
    # review_router reads human_decision to decide next node:
    #   "approve" → publisher → aggregator → END
    #   "revise"  → content_agent (loops back)
    #   "reject"  → rejected → END

    return {
        "human_decision": action,
        "revision_notes": notes,
        "chosen_images":  chosen_images,
        "review_count":   review_count + 1
    }
