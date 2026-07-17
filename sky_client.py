import json
import aiohttp


class SkyMcpClient:
    """封装对本地 sky-mcp-server 的 HTTP 调用"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def _call(self, method_name: str, arguments: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": method_name, "arguments": arguments},
            "id": self._next_id(),
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                return data.get("result", {})

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def screenshot(self) -> str | None:
        """截图，返回 base64 PNG"""
        try:
            result = await self._call("take_screenshot", {})
            content = result.get("content", [])
            for item in content:
                if item.get("type") == "image":
                    return item.get("data")
        except Exception:
            pass
        return None

    async def press_key(self, key: str, duration_ms: int = 80, backend: str = "auto") -> str:
        result = await self._call("press_key", {
            "key": key,
            "duration_ms": duration_ms,
            "backend": backend,
        })
        return self._text(result)

    async def send_chat(self, message: str, backend: str = "auto") -> str:
        result = await self._call("send_chat", {
            "message": message,
            "backend": backend,
        })
        return self._text(result)

    async def status(self) -> dict:
        try:
            result = await self._call("status", {})
            text = self._text(result)
            return json.loads(text)
        except Exception:
            return {}

    def _text(self, result: dict) -> str:
        for item in result.get("content", []):
            if item.get("type") == "text":
                return item.get("text", "")
        return ""
