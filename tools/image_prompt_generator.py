from langchain_core.messages import HumanMessage

def generate_image_prompt(state, style: str = "realistic", platform: str = "generic") -> str:
    """
    Uses Mistral to write a detailed image generation prompt
    based on the post content.
    Mistral understands the context — HuggingFace just sees a prompt.
    """

    llm = state["llm"]

    prompt = f"""
    You are an expert at writing image generation prompts
    for social media posts.

    Based on this content, write a detailed image prompt
    that would create a perfect visual for {platform.upper()}.

    Post content: {state["raw_content"]}
    Brand voice:  {state["brand_voice"]}
    Image style:  {style}

    Rules:
    - Describe scene, mood, colors, lighting clearly
    - Make it visually striking and scroll-stopping
    - Match the brand voice and content theme
    - Format suitable for {platform.upper()}
    - No text or words in the image
    - Under 200 words

    Return only the image prompt. Nothing else.
    """

    response = llm.invoke([HumanMessage(content=prompt)])

    print(f"📝 Image prompt: {response.content[:100]}...")
    return response.content