# nodes/content_agent.py
from langchain_core.messages import HumanMessage
from state import SocialMediaState

def content_agent(state: SocialMediaState) -> dict:
    print("[*] Generating content...")

    # ✅ Safe access with fallbacks — prevents KeyError on revision loop
    llm            = state.get("llm")
    topic          = state.get("topic", "")
    brand_voice    = state.get("brand_voice", "professional")
    platforms      = state.get("target_platforms", [])
    revision_notes = state.get("revision_notes", "")

    # ✅ Include revision feedback if this is a regeneration
    revision_section = f"""
    Previous post was reviewed and needs improvement.
    Human feedback: {revision_notes}
    Please revise based on this feedback.
    """ if revision_notes else ""

    prompt = f"""
    You are a social media content writer.

    Topic: {topic}
    Brand voice: {brand_voice}
    Target platforms: {", ".join(platforms)}
    {revision_section}

    Write a single core message that can be adapted for each platform.
    Keep it concise, engaging, and true to the brand voice.
    Return only the raw content, no explanations.
    Write at least one paragraph.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    return {
        "raw_content":    response.content,
        "formatted_posts": {},   # ✅ Reset formatted posts on regeneration
        "platform_results": {},  # ✅ Reset results on regeneration
        "errors":          [],   # ✅ Reset errors on regeneration
        "image_candidates": {}   # ✅ Reset image candidates on regeneration
    }