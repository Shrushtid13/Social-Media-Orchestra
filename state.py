# state.py
from typing import TypedDict, Literal, Annotated, Optional, Any
import operator
 
 
class SocialMediaState(TypedDict, total=False):
    # ── LLM Config ────────────────────────────────────────────
    # Set once at the start by the user
    # llm_initializer reads these and creates the actual LLM instance
 
    llm_name:    str    # "mistral-large" | "mistral-small" | "mistral-nemo"
    temperature: float  # 0.0 = focused, 1.0 = creative
    llm:         Any    # actual ChatMistralAI instance — filled by llm_initializer
                        # None at start, set after llm_initializer runs
                        # every node reads state["llm"] instead of hardcoding
 
    # ── Input ─────────────────────────────────────────────────
    # Set once at the start, never change throughout the run
 
    topic:            str         # what to post about
    brand_voice:      str         # "professional" | "casual" | "witty" etc
    target_platforms: list[str]   # ["twitter", "instagram", "linkedin"]
    posting_mode:     str         # "simultaneous" | "single"
 
    # ── Image Config ──────────────────────────────────────────
    image_settings: dict
    # Structure per platform:
    # {
    #   "twitter": {
    #     "mode":          "none" | "generate" | "upload" | "both"
    #     "style":         "realistic" | "illustration" | "minimalist" | "cinematic"
    #     "uploaded_path": "path/to/image.png"   ← required for upload and both
    #   },
    #   "instagram": { ... },
    #   "linkedin":  { ... }
    # }
 
    image_candidates: Annotated[dict, lambda a, b: {**a, **b}]
    # Filled by format_and_post when mode = "both"
    # Uses reducer — merged across parallel branches
 
    chosen_images: dict
    # Filled by human_review after user picks from image_candidates
 
    # ── Content Pipeline ──────────────────────────────────────
 
    raw_content: str
    # Filled by content_agent
 
    formatted_posts: Annotated[dict, lambda a, b: {**a, **b}]
    # Filled by format_and_post (one entry per platform)
    # Uses reducer — merged across parallel branches
 
    # ── Human Review ──────────────────────────────────────────
 
    human_decision: str
    # "approve" | "revise" | "reject"
 
    revision_notes: str
    # Feedback from human when revising
 
    review_count: int
    # Incremented each review — max 3
 
    # ── Results ───────────────────────────────────────────────
 
    platform_results: Annotated[dict, lambda a, b: {**a, **b}]
    # Filled by format_and_post, publisher
    # Uses reducer — merged across parallel branches
 
    errors: Annotated[list, operator.add]
    # Accumulated across all nodes and parallel branches
 
    aggregator_summary: dict
    # Final summary from aggregator node
 
    # ── Metadata ──────────────────────────────────────────────
 
    current_platform: str
    # Set by platform_router via Send() for each parallel branch