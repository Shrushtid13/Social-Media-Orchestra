# tools/image_generator.py
import os
import time
import uuid
import requests
from pathlib import Path

HF_MODELS = {
    "realistic":    "black-forest-labs/FLUX.1-schnell",
    "illustration": "black-forest-labs/FLUX.1-schnell",
    "minimalist":   "black-forest-labs/FLUX.1-schnell",
    "cinematic":    "black-forest-labs/FLUX.1-schnell",
}

def generate_image(prompt: str, style: str = "realistic", platform: str = "generic") -> str:
    """
    Generates image using Hugging Face Router API.
    Returns local file path of saved image.
    """

    api_key = os.getenv("HF_API_KEY")

    if not api_key:
        raise EnvironmentError("Image generation limit is over (Missing API Key)")

    model   = HF_MODELS.get(style, HF_MODELS["realistic"])
    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "width":               1024,
            "height":              1024,
            "num_inference_steps": 30,
            "guidance_scale":      7.5,
        }
    }

    max_retries = 5

    for attempt in range(max_retries):
        print(f"[*] Generating image... (attempt {attempt + 1}/{max_retries})")

        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120
        )

        # ── Success ──────────────────────────────────
        if response.status_code == 200:
            print("[+] Image generated successfully")
            return _save_image(response.content, platform)

        # ── Model cold start ─────────────────────────
        if response.status_code == 503:
            wait_time = response.json().get("estimated_time", 30)
            print(f"[!] Model loading... waiting {wait_time:.0f}s")
            time.sleep(wait_time + 5)
            continue

        # -- Rate limited or Out of Credits ----------------
        if response.status_code in [402, 403, 429]:
            raise Exception("Image generation limit is over")

        # -- Any other error ---------------------------
        raise Exception("Image generation limit is over")

    raise Exception(
        f"\n[!] Image generation failed after {max_retries} attempts"
        f"\n[!] Model may be unavailable -- try again later"
    )


def _save_image(image_bytes: bytes, platform: str) -> str:
    """Saves image bytes to disk, returns file path."""

    save_dir = Path("generated_images")
    save_dir.mkdir(exist_ok=True)

    filename = f"{platform}_{uuid.uuid4().hex[:8]}.png"
    filepath = save_dir / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    print(f"[*] Image saved: {filepath}")
    return str(filepath)