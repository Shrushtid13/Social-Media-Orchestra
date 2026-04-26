# test_image.py
from dotenv import load_dotenv
from tools.image_generator import generate_image

load_dotenv()

path = generate_image(
    prompt="A sleek modern laptop on a clean white desk, professional photography",
    style="realistic"
)

print(f"\n[+] Image ready at: {path}")