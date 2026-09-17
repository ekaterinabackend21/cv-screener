import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from generation.models import CandidateProfile
from settings import Settings


def generate_portrait(profile: CandidateProfile, *, settings: Settings) -> bytes:
    """Generate a fictional professional headshot through the provider image API."""
    model_name = settings.image_model.strip()
    if not model_name:
        raise ValueError("Set IMAGE_MODEL to an image model available in the API catalog.")
    _, base_url, api_key = settings.model_credentials()
    prompt = (
            "Generate a realistic professional headshot photo for a fictional CV candidate. "
            f"The candidate is {profile.first_name} {profile.last_name}, a {profile.position}. "
            f"They are based in {profile.location}. Use a neutral studio background, natural "
            "expression, business-casual clothing, centered face and shoulders, portrait crop. "
            "Do not add text, logos, props or watermarks. This is a synthetic person, not a real person."
    )
    payload = json.dumps(
        {
            "model": model_name,
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "quality": "low",
            "n": 1,
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/images",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key.get_secret_value().strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image API request failed with HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to image API: {exc.reason}") from exc

    try:
        encoded = body["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Image API returned an unexpected response without image data.") from exc
    if not encoded:
        raise ValueError("The image provider returned no base64 image data.")
    return base64.b64decode(encoded)
