from langchain_core.messages import HumanMessage
from tools.image_handler import resolve_image

def format_for_linkedin(state) -> dict:
    llm = state["llm"]

    prompt = f"""
    Adapt this content for LinkedIn.
    Rules:
    - Professional but human tone
    - Strong opening hook line
    - Line breaks between paragraphs
    - End with an engaging question
    - 1-3 professional hashtags
    - Tone: {state["brand_voice"]}
    Raw content: {state["raw_content"]}
    Return only the post text. Nothing else.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    caption  = response.content

    image_result = resolve_image("linkedin", state)

    return {
        "caption":      caption,
        "image_result": image_result
    }