from langchain_core.messages import HumanMessage
from tools.image_handler import resolve_image

def format_for_facebook(state) -> dict:
    llm = state["llm"]

    prompt = f"""
    Adapt this content for Facebook.
    Rules:
    - Engaging and community-focused
    - Use emojis where appropriate
    - Link in bio or clear next step
    - Tone: {state["brand_voice"]}
    Raw content: {state["raw_content"]}
    Return only the post text. Nothing else.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    caption  = response.content

    # Facebook supports text only or with image
    image_result = resolve_image("facebook", state)

    return {
        "caption":      caption,
        "image_result": image_result
    }
