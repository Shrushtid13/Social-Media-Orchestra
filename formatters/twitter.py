import re
from langchain_core.messages import HumanMessage
from tools.image_handler import resolve_image


def clean_caption(caption: str) -> str:
    # Remove meta-commentary like *(380+ chars, punchy...)*
    caption = re.sub(r'\*\(.*?\)\*', '', caption)
    # Remove ** bold markdown
    caption = caption.replace('**', '')
    # Remove * italic markdown
    caption = caption.replace('*', '')
    # Remove lines starting with ( and ending with )
    caption = re.sub(r'^\(.*?\)$', '', caption, flags=re.MULTILINE)
    # Strip extra whitespace and newlines
    caption = caption.strip()
    return caption


def format_for_twitter(state) -> dict:
    llm = state["llm"]

    # ── Generate Caption ──────────────────────────────
    prompt = f"""
    Adapt this content for Twitter/X.

    Rules:
    - Maximum 280 characters (strict — Twitter's hard limit)
    - 1-2 relevant hashtags included in the 280 characters
    - Punchy, engaging, and concise
    - Tone: {state["brand_voice"]}
    - Return ONLY the tweet text
    - No explanations, notes, labels, or meta-commentary
    - No asterisks, no parentheses with descriptions
    - No character counts or performance notes

    Raw content: {state["raw_content"]}
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    caption  = clean_caption(response.content)

    # ── Truncate as safety net (280 chars hard limit) ─
    if len(caption) > 280:
        caption = caption[:277] + "..."

    # ── Resolve Image ─────────────────────────────────
    image_result = resolve_image("twitter", state)

    return {
        "caption":      caption,
        "image_result": image_result
    }