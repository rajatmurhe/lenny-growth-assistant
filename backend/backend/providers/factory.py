from backend.providers.base import LLMProvider
from backend.providers.ollama import OllamaProvider
from backend.providers.anthropic import AnthropicProvider
from backend.config import Settings

def get_provider(provider_name: str, config: Settings) -> LLMProvider:
    if provider_name == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()

def get_embed_provider(config: Settings) -> LLMProvider:
    return OllamaProvider()
