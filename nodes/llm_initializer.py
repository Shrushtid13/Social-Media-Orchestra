# nodes/llm_initializer.py
from llm_factory import get_llm
from state import SocialMediaState

def llm_initializer(state: SocialMediaState) -> dict:
    llm_name    = state.get("llm_name",    "mistral-large")
    temperature = state.get("temperature", 0.7)

    print(f"[*] Initializing: {llm_name}")
    llm = get_llm(llm_name, temperature)

    return {"llm": llm}