from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from settings import Settings


def create_text_model(settings: Settings) -> Model:
    """Configure an OpenAI-compatible chat model without sending an API request."""
    model_name, base_url, key = settings.model_credentials()
    openai_provider = OpenAIProvider(
        api_key=key.get_secret_value(),
        base_url=base_url,
    )
    return OpenAIChatModel(model_name, provider=openai_provider)
