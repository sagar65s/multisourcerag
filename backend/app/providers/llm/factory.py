import json
import os

from app.core.config import Settings
from app.providers.llm.http_providers import GeminiProvider, OpenAICompatibleProvider
from app.providers.llm.registry import LLMProviderRegistry


def build_llm_registry(settings: Settings) -> LLMProviderRegistry:
    registry = LLMProviderRegistry()
    factories = {
        "gemini": lambda priority: GeminiProvider(settings.gemini_model, settings.gemini_api_key or "", priority),
        "groq": lambda priority: OpenAICompatibleProvider("groq", settings.groq_model, settings.groq_api_key or "", "https://api.groq.com/openai/v1", priority, "GROQ_API_KEY", retries=settings.provider_retry_count),
        "mistral": lambda priority: OpenAICompatibleProvider("mistral", settings.mistral_model, settings.mistral_api_key or "", "https://api.mistral.ai/v1", priority, "MISTRAL_API_KEY", retries=settings.provider_retry_count),
        "openrouter": lambda priority: OpenAICompatibleProvider("openrouter", settings.openrouter_model, settings.openrouter_api_key or "", "https://openrouter.ai/api/v1", priority, "OPENROUTER_API_KEY", retries=settings.provider_retry_count),
    }
    custom: dict[str, dict] = {}
    try:
        decoded = json.loads(settings.custom_llm_providers_json)
        custom = {str(item["name"]): item for item in decoded if isinstance(item, dict) and item.get("name") and item.get("model") and item.get("base_url") and item.get("api_key_env")}
    except (ValueError, TypeError):
        custom = {}
    names = [*settings.llm_provider_names, *(name for name in custom if name not in settings.llm_provider_names)]
    for priority, name in enumerate(names):
        if name in factories:
            provider = factories[name](priority)
            if name == "gemini": provider.descriptor.api_key_env_name = "GEMINI_API_KEY"; provider.descriptor.retries = settings.provider_retry_count
            registry.register(provider)
        elif name in custom:
            item = custom[name]; env_name = str(item["api_key_env"])
            registry.register(OpenAICompatibleProvider(name, str(item["model"]), os.getenv(env_name, ""), str(item["base_url"]), priority, env_name, int(item.get("timeout", 45)), int(item.get("retries", settings.provider_retry_count)), int(item.get("rpm", 0)), int(item.get("daily_quota", 0)), int(item.get("context_size", 0))))
    return registry
