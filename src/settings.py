from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_model: str = "gpt-5.6-luna"
    image_model: str = "gpt-image-1-mini"
    image_generation_enabled: bool = True
    output_dir: str = "generated_cvs"
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "cv_candidates"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    api_key: SecretStr = SecretStr("")
    base_url: str = "https://api.relaymodels.com/v1"

    def model_credentials(self) -> tuple[str, str, SecretStr]:
        """Validate and return the model ID, API base URL and secret API key."""
        model_name = self.llm_model.strip()
        base_url = self.base_url.strip()
        if not model_name:
            raise ValueError("Set LLM_MODEL to a model ID from the provider's catalog.")
        if model_name.startswith(("openai:", "openai-responses:", "anthropic:")):
            raise ValueError("Use a plain model ID in LLM_MODEL, without a provider prefix.")
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("Set BASE_URL to an HTTP or HTTPS API endpoint.")
        if not self.api_key.get_secret_value().strip():
            raise ValueError("Set API_KEY in .env or the environment.")
        return model_name, base_url, self.api_key
