import base64

from openai import OpenAI

from generation.models import CandidateProfile
from settings import Settings


def generate_portrait(profile: CandidateProfile, *, settings: Settings) -> bytes:
    """Generate a fictional professional headshot and return its PNG bytes."""
    model_name = settings.image_model.strip()
    if not model_name:
        raise ValueError("Set IMAGE_MODEL to an image model available in the API catalog.")
    _, base_url, api_key = settings.model_credentials()
    client = OpenAI(api_key=api_key.get_secret_value(), base_url=base_url)
    response = client.images.generate(
        model=model_name,
        prompt=(
            "Generate a realistic professional headshot photo for a fictional CV candidate. "
            f"The candidate is {profile.first_name} {profile.last_name}, a {profile.position}. "
            f"They are based in {profile.location}. Use a neutral studio background, natural "
            "expression, business-casual clothing, centered face and shoulders, portrait crop. "
            "Do not add text, logos, props or watermarks. This is a synthetic person, not a real person."
        ),
        size="1024x1024",
        quality="low",
    )
    encoded = response.data[0].b64_json
    if not encoded:
        raise ValueError("The image provider returned no base64 image data.")
    return base64.b64decode(encoded)
