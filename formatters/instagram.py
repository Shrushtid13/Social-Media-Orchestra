from langchain_core.messages import HumanMessage
from tools.image_handler import resolve_image

def format_for_instagram(state) -> dict:
    llm = state["llm"]

    prompt = f"""
    Adapt this content for Instagram.
    Rules:
    - Conversational and visual language
    - 3-5 relevant hashtags at the end
    - Use line breaks for readability
    - Clear call to action
    - Tone: {state["brand_voice"]}
    Raw content: {state["raw_content"]}
    Return only the caption text. Nothing else.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    caption  = response.content

    # Instagram always needs image — enforce it
    image_settings = state.get("image_settings", {})
    ig_mode        = image_settings.get("instagram", {}).get("mode", "generate")

    if ig_mode == "none":
        print("⚠️  Instagram requires image — switching to generate")
        state["image_settings"]["instagram"]["mode"] = "generate"

    image_result = resolve_image("instagram", state)

    return {
        "caption":      caption,
        "image_result": image_result
    }