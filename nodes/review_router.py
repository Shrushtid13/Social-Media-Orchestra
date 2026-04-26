# nodes/review_router.py
from state import SocialMediaState

def route_after_review(state: SocialMediaState) -> str:
    """
    Decides what happens based on human decision.
    Returns the name of the next node to run.
    """
    decision     = state["human_decision"]
    review_count = state["review_count"]

    if decision == "approve":
        print("✅ Approved — proceeding to publish")
        return "publish"

    elif decision == "reject":
        print("❌ Rejected — stopping")
        return "rejected"

    elif decision == "revise":
        # Safety limit — don't loop forever
        if review_count >= 3:
            print("⚠️ Max revisions reached — stopping")
            return "rejected"
        print(f"🔄 Revision requested (attempt {review_count}/3) — regenerating")
        return "content_agent"   # go all the way back to start

    # Default safety
    return "rejected"