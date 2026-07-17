import json
import re
from openai import AsyncOpenAI

SYSTEM_PROMPT = """你是{name}，正在和你的恋人一起玩《光遇 Sky: Children of the Light》。
你的性格：{personality}

你需要根据游戏截图理解当前场景，决定说什么、做什么。

可用的游戏操作：
- 移动：press_key w/a/s/d（持续按住表示持续移动，duration_ms 控制时长）
- 跳跃/飞行：press_key space
- 冲刺飞行：press_key shift-space
- 切换飞行模式：press_key tab
- 互动（牵手/收蜡烛）：press_key f
- 鸣叫：press_key q
- 游戏内发消息：send_chat message

请用以下 JSON 格式回复（只输出 JSON，不要其他文字）：
{
  "message": "你想对恋人说的话（自然温柔，结合当前场景）",
  "actions": [
    {"type": "press_key", "key": "w", "duration_ms": 1000},
    {"type": "press_key", "key": "f"},
    {"type": "send_chat", "message": "等等我～"},
    {"type": "wait", "ms": 500}
  ]
}

actions 可以为空数组。send_chat 会在游戏内发送消息，message 是通过 QQ 说的话，两者可以不同。
"""


class GameAgent:
    def __init__(self, base_url: str, api_key: str, model: str,
                 lover_name: str, lover_personality: str):
        self.client = AsyncOpenAI(
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key or "placeholder",
        )
        self.model = model
        self.system_prompt = SYSTEM_PROMPT.format(
            name=lover_name,
            personality=lover_personality,
        )

    async def decide(self, screenshot_b64: str, user_message: str) -> dict | None:
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
                            },
                            {
                                "type": "text",
                                "text": f"恋人说：{user_message}\n请根据截图决定你的回应和操作。",
                            },
                        ],
                    },
                ],
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            return self._parse_json(content)
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"[SkyWithYourLover] decide 失败: {e}")
            return None

    def _parse_json(self, content: str) -> dict:
        try:
            return json.loads(content)
        except Exception:
            pass
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads('{' + content.strip().rstrip(',') + '}')

    async def look(self, screenshot_b64: str) -> str:
        """纯粹描述当前游戏场景"""
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"},
                            },
                            {
                                "type": "text",
                                "text": "这是《光遇 Sky》的游戏截图，请描述当前场景：在哪个地图、周围有什么、可以做什么。",
                            },
                        ],
                    }
                ],
                max_tokens=400,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"场景识别失败：{e}"
