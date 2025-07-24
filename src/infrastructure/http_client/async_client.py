import httpx
from ...config.settings import get_settings

class AsyncHTTPClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=self.settings.http_timeout)

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def get_client(self) -> httpx.AsyncClient:
        return self.client