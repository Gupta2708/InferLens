from app.llm.base import Provider


class ProviderRegistry:
    """Owns provider adapters so gateway routing never depends on SDK shapes."""

    def __init__(self, providers: list[Provider]):
        self._providers = {provider.provider: provider for provider in providers}

    def get(self, provider: str) -> Provider:
        return self._providers[provider]

    def names(self) -> list[str]:
        return sorted(self._providers)

    async def health(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for name, adapter in self._providers.items():
            try:
                result[name] = await adapter.health_check()
            except Exception:
                result[name] = {"status": "unavailable"}
        return result
