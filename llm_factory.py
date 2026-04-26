# llm_factory.py
import os
from dotenv import load_dotenv

load_dotenv()

# ── Mistral Models Registry ──────────────────────────────────

MISTRAL_MODELS = {
    "mistral-large": "mistral-large-latest",   # best quality
    "mistral-small": "mistral-small-latest",   # fast + cheap
    "mistral-nemo":  "open-mistral-nemo",      # free tier
    "codestral":     "codestral-latest",       # code focused
}


def get_llm(llm_name: str, temperature: float = 0.7):
    """
    Creates a Mistral LLM instance.
    Validates API key and model name before attempting connection.
    """

    # Step 1: Validate model name
    if llm_name not in MISTRAL_MODELS:
        raise ValueError(
            f"\n Unknown Mistral model: '{llm_name}'"
            f"\n Available models: {list(MISTRAL_MODELS.keys())}"
        )

    # Step 2: Validate API key exists
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError(
            f"\n Missing Mistral API key"
            f"\n Add this to your .env file:"
            f"\n   MISTRAL_API_KEY=your_key_here"
            f"\n Get your key from: https://console.mistral.ai/api-keys"
        )

    # Step 3: Import and create
    try:
        from langchain_mistralai import ChatMistralAI

        model_id = MISTRAL_MODELS[llm_name]

        llm = ChatMistralAI(
            model=model_id,
            temperature=temperature,
            api_key=api_key
        )

        print(f" Mistral ready: {llm_name} ({model_id})")
        return llm

    except ImportError:
        raise ImportError(
            f"\n Mistral package not installed"
            f"\n Run: pip install langchain-mistralai"
        )


def get_available_models() -> dict:
    """
    Returns all Mistral models with availability status.
    Used by React dropdown to show what's usable.
    """

    api_key    = os.getenv("MISTRAL_API_KEY")
    configured = bool(api_key)

    return {
        model_name: {
            "provider":   "mistral",
            "model_id":   model_id,
            "configured": configured
        }
        for model_name, model_id in MISTRAL_MODELS.items()
    }