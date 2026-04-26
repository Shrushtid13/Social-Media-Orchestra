# graph.py
from langgraph.graph             import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import SocialMediaState

# ── Node imports ─────────────────────────────────────────────
from nodes.llm_initializer import llm_initializer
from nodes.content_agent   import content_agent
from nodes.platform_router import platform_router
from nodes.format_and_post import format_and_post
from nodes.human_review    import human_review_node
from nodes.review_router   import route_after_review
from nodes.publisher       import publisher
from nodes.aggregator      import aggregator


# ── Helper node ──────────────────────────────────────────────
def rejected_node(state: SocialMediaState) -> dict:
    print("🚫 Post rejected — workflow ended")
    return {}


# ══════════════════════════════════════════════════════════════
def build_graph() -> StateGraph:
    """
    Full social media automation graph.

    Complete Flow:
    llm_initializer
        → content_agent
            → platform_router (fan-out via conditional edges)
                → format_and_post × N (parallel)
                  each branch:
                    - generates caption via Mistral
                    - resolves image:
                        none     → text only
                        generate → HuggingFace generates image
                        upload   → uses uploaded image
                        both     → generates + uploaded
                                   (user picks at review)
                    - posts immediately (except "both" mode)
                      "both" mode → stores candidates → posts after review
                → human_review (interrupt — graph pauses here)
                    → approve  → publisher → aggregator → END
                    → revise   → content_agent (loops back)
                    → reject   → rejected → END
    """

    builder = StateGraph(SocialMediaState)

    # ── Register nodes ────────────────────────────────────────

    builder.add_node("llm_initializer", llm_initializer)
    # Creates Mistral LLM instance from llm_name + temperature
    # Puts it in state["llm"] for all nodes to use

    builder.add_node("content_agent",   content_agent)
    # Reads state["llm"] + state["topic"] + state["brand_voice"]
    # Writes raw platform-agnostic content to state["raw_content"]

    # NOTE: platform_router is NOT registered as a node
    # It is used as a conditional edge function from content_agent
    # It returns list of Send() objects — one per platform
    # LangGraph runs them all simultaneously (fan-out)

    builder.add_node("format_and_post", format_and_post)
    # Runs once per platform in parallel
    # Reads state["current_platform"] to know which platform it is
    # Calls correct formatter (twitter/instagram/linkedin)
    # Resolves image based on image_settings per platform:
    #   none     → text only post
    #   generate → HuggingFace generates image
    #   upload   → uses user uploaded image
    #   both     → generates + stores both as candidates
    #              posts after human picks one at review
    # Posts immediately for none/generate/upload modes
    # Writes to state["formatted_posts"] + state["platform_results"]
    # Writes to state["image_candidates"] for "both" mode platforms

    builder.add_node("human_review",    human_review_node)
    # interrupt() pauses graph completely here
    # State saved to MemorySaver
    # Shows formatted posts + image candidates to human
    # For "both" mode platforms: human picks generated or uploaded
    # Human sets action: approve / revise / reject
    # Writes state["human_decision"] + state["chosen_images"]

    builder.add_node("publisher",       publisher)
    # Runs after human approves
    # Handles "both" mode platforms that were pending image choice
    # Posts them now using the chosen image
    # Writes final results to state["platform_results"]

    builder.add_node("aggregator",      aggregator)
    # Collects all platform_results
    # Prints summary: successes, failures, URLs, post IDs
    # Writes state["aggregator_summary"] for FastAPI to return

    builder.add_node("rejected",        rejected_node)
    # Simple terminal node
    # Prints rejection message
    # Leads to END

    # ── Entry point ───────────────────────────────────────────
    builder.set_entry_point("llm_initializer")

    # ── Sequential edges ──────────────────────────────────────

    # LLM created → generate content
    builder.add_edge("llm_initializer", "content_agent")

    # All parallel format_and_post branches finish → human review
    # LangGraph automatically waits for ALL parallel branches
    # before moving to human_review
    builder.add_edge("format_and_post", "human_review")

    # Publisher done → aggregate and summarize
    builder.add_edge("publisher",       "aggregator")

    # Aggregator done → end
    builder.add_edge("aggregator",      END)

    # Rejected → end immediately
    builder.add_edge("rejected",        END)

    # ── Conditional edges ─────────────────────────────────────

    # Fan-out from content_agent using platform_router as edge function
    # platform_router returns [Send("format_and_post", {...}), ...]
    # LangGraph fans out — one format_and_post per platform in parallel
    builder.add_conditional_edges(
        "content_agent",
        platform_router,        # ✅ used as edge function, NOT a node
        ["format_and_post"]     # all Send() objects point here
    )

    # After human review → route based on decision
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "publish":       "publisher",     # approved → post "both" mode + summarize
            "content_agent": "content_agent", # revise   → loop back to regenerate
            "rejected":      "rejected"       # reject   → cancel workflow
        }
    )

    # ── Compile with checkpointer ─────────────────────────────
    # MemorySaver is REQUIRED for interrupt() in human_review
    # Without it, the graph cannot pause and resume
    memory = MemorySaver()

    return builder.compile(checkpointer=memory)


# ── Singleton ─────────────────────────────────────────────────
# Import this in backend/main.py and app.py (Streamlit)
graph = build_graph()