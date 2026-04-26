import os
import uuid
from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()

from graph import graph


# ══════════════════════════════════════════════════════════════
# INITIAL STATE BUILDER
# ══════════════════════════════════════════════════════════════

def build_initial_state(
    topic:            str,
    brand_voice:      str,
    target_platforms: list[str],
    posting_mode:     str,
    llm_name:         str,
    temperature:      float,
    image_settings:   dict,
) -> dict:
    """
    Builds the complete initial state for the graph.
    Every field must be present — LangGraph requires
    all TypedDict fields to be initialized.
    """

    return {
        # ── LLM Config ────────────────────────────────
        "llm_name":    llm_name,
        "temperature": temperature,
        "llm":         None,          # filled by llm_initializer

        # ── Input ─────────────────────────────────────
        "topic":            topic,
        "brand_voice":      brand_voice,
        "target_platforms": target_platforms,
        "posting_mode":     posting_mode,

        # ── Image Config ──────────────────────────────
        "image_settings":   image_settings,
        "image_candidates": {},       # filled by format_and_post (both mode)
        "chosen_images":    {},       # filled by human_review

        # ── Content Pipeline ──────────────────────────
        "raw_content":    "",         # filled by content_agent
        "formatted_posts": {},        # filled by format_and_post

        # ── Human Review ──────────────────────────────
        "human_decision": "",         # filled by human_review
        "revision_notes": "",         # filled by human_review
        "review_count":   0,          # incremented each review cycle

        # ── Results ───────────────────────────────────
        "platform_results":   {},     # filled by format_and_post + publisher
        "errors":             [],     # collected across all nodes
        "aggregator_summary": {},     # filled by aggregator

        # ── Metadata ──────────────────────────────────
        "current_platform": "",       # set per parallel branch by router
    }


# ══════════════════════════════════════════════════════════════
# PHASE 1 — RUN UNTIL HUMAN REVIEW
# ══════════════════════════════════════════════════════════════

def run_until_review(initial_state: dict, config: dict) -> dict:
    """
    Runs the graph from the start until it hits
    the interrupt() in human_review_node.

    Returns the current graph state at the pause point.
    """

    print("\n" + "="*55)
    print("[>>>] STARTING SOCIAL MEDIA AUTOMATION")
    print("="*55)
    print("[*] Topic:     " + initial_state['topic'][:60])
    print("[*] Platforms: " + str(initial_state['target_platforms']))
    print("[*] Model:     " + initial_state['llm_name'])
    print("[*] Temp:      " + str(initial_state['temperature']))
    print("[*] Mode:      " + initial_state['posting_mode'])
    print("="*55 + "\n")

    # Run graph — pauses at human_review interrupt()
    graph.invoke(initial_state, config)

    # Get state at the pause point
    current_state = graph.get_state(config)
    return current_state.values


# ══════════════════════════════════════════════════════════════
# PHASE 2 — HUMAN REVIEW (TERMINAL)
# ══════════════════════════════════════════════════════════════

def show_review(state_values: dict) -> dict:
    """
    Shows all formatted posts to the human.
    Handles image choices for "both" mode platforms.
    Collects approve / revise / reject decision.
    Returns the decision dict.
    """

    formatted_posts  = state_values.get("formatted_posts",  {})
    image_candidates = state_values.get("image_candidates", {})
    review_count     = state_values.get("review_count",     0)

    print("\n" + "="*55)
    print("[#] HUMAN REVIEW  (Round " + str(review_count + 1) + ")")
    print("="*55)

    # ── Show each platform post ────────────────────────
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
        print(caption)
        print(f"({len(caption)} characters)")

    # -- Image choices for "both" mode -----------------
    image_choices = {}

    if image_candidates:
        print("\n" + "="*55)
        print("[#] IMAGE CHOICES REQUIRED")
        print("="*55)

        for platform, candidates in image_candidates.items():
            print(f"\n[IMAGE] {platform.upper()}")
            print(f"   Option A - AI Generated : {candidates['generated']}")
            print(f"   Option B - Your Upload  : {candidates['uploaded']}")

            while True:
                choice = input(
                    f"\n   Which image for {platform}? "
                    f"(a = generated / b = uploaded): "
                ).strip().lower()

                if choice == "a":
                    image_choices[platform] = "generated"
                    print(f"   ✅ Chose: AI Generated")
                    break
                elif choice == "b":
                    image_choices[platform] = "uploaded"
                    print(f"   ✅ Chose: Your Upload")
                    break
                else:
                    print("   ⚠️  Please enter 'a' or 'b'")

    # ── Collect decision ───────────────────────────────
    print("\n" + "="*55)
    print("📋 YOUR DECISION")
    print("="*55)
    print("  1 → ✅ Approve & Publish")
    print("  2 → 🔄 Revise & Regenerate")
    print("  3 → ❌ Reject & Cancel")

    while True:
        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "1":
            action = "approve"
            notes  = ""
            print("[OK] Approved!")
            break

        elif choice == "2":
            action = "revise"
            notes  = input(
                "[*] Enter revision notes "
                "(what should change?): "
            ).strip()
            print(f"[REVISE] Revision requested: {notes}")
            break

        elif choice == "3":
            action = "reject"
            notes  = input(
                "[*] Reason for rejection (optional): "
                ).strip()
            print("[REJECT] Rejected.")
            break

        else:
            print("⚠️  Please enter 1, 2, or 3")

    return {
        "action":        action,
        "notes":         notes,
        "image_choices": image_choices
    }


# ══════════════════════════════════════════════════════════════
# PHASE 3 — RESUME AFTER REVIEW
# ══════════════════════════════════════════════════════════════

def resume_after_review(decision: dict, config: dict) -> dict:
    """
    Resumes the paused graph with the human decision.
    Returns the final result.
    """

    print("[>] Resuming graph with decision: " + decision['action'])

    result = graph.invoke(
        Command(resume=decision),
        config
    )

    return result


# ══════════════════════════════════════════════════════════════
# SHOW FINAL RESULTS
# ══════════════════════════════════════════════════════════════

def show_final_results(result: dict):
    """
    Prints the final results after the graph completes.
    """

    summary          = result.get("aggregator_summary", {})
    formatted_posts  = result.get("formatted_posts",    {})

    total     = summary.get("total",     0)
    succeeded = summary.get("succeeded", 0)
    failed    = summary.get("failed",    0)
    successes = summary.get("successes", {})
    failures  = summary.get("failures",  {})

    print("\n" + "="*55)
    print("🎉 FINAL RESULTS")
    print("="*55)

    # -- Successes --------------------------------------
    if successes:
        print(f"\n[OK] Successfully posted ({succeeded}/{total}):")
        for platform, info in successes.items():
            url     = info.get("url",     "N/A")
            post_id = info.get("post_id", "N/A")
            is_mock = info.get("mock",    False)
            mock_label = " [MOCK]" if is_mock else ""

            print(f"\n   [PLATFORM] {platform.upper()}{mock_label}")
            print(f"      Post ID : {post_id}")
            print(f"      URL     : {url}")

            caption = formatted_posts.get(platform, "")
            if caption:
                preview = (
                    caption[:100] + "..."
                    if len(caption) > 100
                    else caption
                )
                print(f"      Preview : {preview}")

    # -- Failures ---------------------------------------
    if failures:
        print(f"\n[X] Failed ({failed}/{total}):")
        for platform, error in failures.items():
            print(f"\n   [PLATFORM] {platform.upper()}")
            print(f"      Error: {error}")

    # ── Overall verdict ────────────────────────────────
    print("\n" + "-"*55)
    if failed == 0 and total > 0:
        print(f"🎊 All {total} platform(s) posted successfully!")
    elif succeeded == 0:
        print(f"💔 All {total} platform(s) failed.")
    else:
        print(f"⚠️  {succeeded}/{total} succeeded, {failed} failed.")
    print("="*55 + "\n")


# ══════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════

def run_automation(
    topic:            str,
    brand_voice:      str       = "professional",
    target_platforms: list[str] = None,
    posting_mode:     str       = "simultaneous",
    llm_name:         str       = "mistral-large",
    temperature:      float     = 0.7,
    image_settings:   dict      = None,
):
    """
    Main entry point for the automation system.
    Handles the full loop including revision cycles.
    """

    if target_platforms is None:
        target_platforms = ["twitter", "instagram", "linkedin", "facebook"]

    if image_settings is None:
        image_settings = {
            p: {"mode": "none"}
            for p in target_platforms
        }

    # Unique thread ID per run
    # Same thread_id used across all invoke() calls
    # so LangGraph can resume the same paused graph
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }

    # Build initial state
    initial_state = build_initial_state(
        topic=            topic,
        brand_voice=      brand_voice,
        target_platforms= target_platforms,
        posting_mode=     posting_mode,
        llm_name=         llm_name,
        temperature=      temperature,
        image_settings=   image_settings,
    )

    # ── Phase 1: Run until review ──────────────────────
    state_values = run_until_review(initial_state, config)

    # ── Review loop ────────────────────────────────────
    # Loops until user approves or rejects
    # Each revision loops back through content_agent
    # → platform formatters → human_review again

    while True:
        # ── Phase 2: Human reviews ─────────────────────
        decision = show_review(state_values)
        action   = decision["action"]

        # ── Phase 3: Resume graph ──────────────────────
        result = resume_after_review(decision, config)

        # Rejected → stop
        if action == "reject":
            print("\n🚫 Workflow cancelled by user.")
            break

        # Revise → graph looped back → show review again
        if action == "revise":
            print("\n🔄 Content regenerated — showing updated posts...")
            # Get fresh state after revision
            current_state = graph.get_state(config)
            state_values  = current_state.values
            continue

        # Approved -> show results -> done
        if action == "approve":
            show_final_results(result)
            break


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Example 1: Text only, all platforms ───────────
    run_automation(
        topic            = "We just launched a new AI feature that saves teams 2 hours daily!",
        brand_voice      = "professional",
        target_platforms = ["twitter", "instagram", "linkedin", "facebook"],
        posting_mode     = "simultaneous",
        llm_name         = "mistral-large",
        temperature      = 0.7,
        image_settings   = {
            "twitter":   {"mode": "none"},
            "instagram": {"mode": "generate", "style": "realistic"},
            "linkedin":  {"mode": "none"},
            "facebook":  {"mode": "none"},
        }
    )


    # ── Example 2: All platforms with AI images ────────
    # run_automation(
    #     topic            = "Big product launch announcement!",
    #     brand_voice      = "excited and energetic",
    #     target_platforms = ["twitter", "instagram", "linkedin"],
    #     posting_mode     = "simultaneous",
    #     llm_name         = "mistral-large",
    #     temperature      = 0.9,
    #     image_settings   = {
    #         "twitter":   {"mode": "generate", "style": "cinematic"},
    #         "instagram": {"mode": "generate", "style": "realistic"},
    #         "linkedin":  {"mode": "generate", "style": "minimalist"},
    #     }
    # )


    # ── Example 3: Instagram with both options ─────────
    # run_automation(
    #     topic            = "Behind the scenes at our office",
    #     brand_voice      = "casual and friendly",
    #     target_platforms = ["instagram"],
    #     posting_mode     = "single",
    #     llm_name         = "mistral-small",
    #     temperature      = 0.7,
    #     image_settings   = {
    #         "instagram": {
    #             "mode":          "both",
    #             "style":         "cinematic",
    #             "uploaded_path": "uploads/office_photo.jpg"
    #         }
    #     }
    # )


    # ── Example 4: Twitter only, fast model ───────────
    # run_automation(
    #     topic            = "Quick tip: use keyboard shortcuts to save time",
    #     brand_voice      = "witty and educational",
    #     target_platforms = ["twitter"],
    #     posting_mode     = "single",
    #     llm_name         = "mistral-nemo",
    #     temperature      = 0.8,
    #     image_settings   = {
    #         "twitter": {"mode": "none"}
    #     }
    # )