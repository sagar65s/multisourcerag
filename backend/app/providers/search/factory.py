import json
import os

from app.core.config import Settings
from app.providers.search.ddgs import DDGSProvider
from app.providers.search.registry import SearchProviderRegistry
from app.providers.search.tavily import TavilyProvider
from app.providers.search.custom_provider import CustomSearchProvider


def build_search_registry(settings: Settings) -> SearchProviderRegistry:
    registry = SearchProviderRegistry(); factories = {"tavily": lambda priority: TavilyProvider(settings.tavily_api_key or "", priority), "ddgs": lambda priority: DDGSProvider(priority)}
    try:
        decoded = json.loads(settings.custom_search_providers_json); custom = {str(item["name"]): item for item in decoded if isinstance(item, dict) and item.get("name") and item.get("base_url")}
    except (ValueError, TypeError): custom = {}
    configured = [item.strip() for item in settings.search_provider_order.split(",") if item.strip()]
    names = [*configured, *(name for name in custom if name not in configured)]
    for priority, name in enumerate(names):
        if name in factories: registry.register(factories[name](priority))
        elif name in custom:
            item = custom[name]; env_name = str(item.get("api_key_env") or ""); registry.register(CustomSearchProvider(name, priority, str(item["base_url"]), os.getenv(env_name, "") if env_name else "", str(item.get("method", "POST")), str(item.get("query_parameter", "query")), int(item.get("timeout", 20)), int(item.get("rpm", 0)), int(item.get("daily_quota", 0)), env_name or None))
    return registry
import json
import os
