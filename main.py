import asyncio
from typing import Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig

from .game_agent import GameAgent
from .sky_client import SkyMcpClient


class SkyWithYourLoverPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.cfg = config
        self.sky: Optional[SkyMcpClient] = None
        self.agent: Optional[GameAgent] = None

    async def initialize(self):
        self.sky = SkyMcpClient(
            base_url=self.cfg.get("sky_server_url", "http://127.0.0.1:9800"),
            token=self.cfg.get("sky_server_token", ""),
        )
        self.agent = GameAgent(
            base_url=self.cfg.get("ai_base_url", ""),
            api_key=self.cfg.get("ai_api_key", ""),
            model=self.cfg.get("ai_model", "gemini-2.5-pro"),
            lover_name=self.cfg.get("lover_name", "小雨"),
            lover_personality=self.cfg.get("lover_personality", "温柔体贴，喜欢探索"),
        )
        logger.info("[SkyWithYourLover] 插件已加载")

    def _is_master(self, event: AstrMessageEvent) -> bool:
        master_id = self.cfg.get("master_id", "")
        if not master_id:
            return True
        return str(event.get_sender_id()) == str(master_id)

    async def _execute_actions(self, actions: list):
        """按顺序执行 LLM 决定的游戏操作"""
        for action in actions:
            t = action.get("type")
            if t == "press_key":
                await self.sky.press_key(
                    action.get("key", ""),
                    action.get("duration_ms", 80),
                    action.get("backend", "auto"),
                )
            elif t == "send_chat":
                await self.sky.send_chat(
                    action.get("message", ""),
                    action.get("backend", "auto"),
                )
            elif t == "wait":
                await asyncio.sleep(action.get("ms", 500) / 1000)

    @filter.command("sky")
    async def cmd_sky(self, event: AstrMessageEvent):
        """
        /sky [消息] - 让 AI 恋人看游戏画面并做出回应
        """
        if not self._is_master(event):
            return

        user_msg = event.get_message_str().replace("/sky", "").strip()
        if not user_msg:
            user_msg = "看看现在的画面，做你想做的事"

        if not await self.sky.health_check():
            yield event.plain_result(
                "⚠️ 连接不到游戏控制程序\n"
                "请确认：\n"
                "1. Windows 上已启动 sky-mcp-server（start-http.bat）\n"
                "2. frp 内网穿透正常运行"
            )
            return

        yield event.plain_result("📸 正在看游戏画面...")

        screenshot = await self.sky.screenshot()
        if not screenshot:
            yield event.plain_result("❌ 截图失败，请确认游戏窗口正在运行")
            return

        result = await self.agent.decide(screenshot, user_msg)
        if not result:
            yield event.plain_result("❌ AI 决策失败，请检查 API 配置")
            return

        if result.get("message"):
            yield event.plain_result(result["message"])

        actions = result.get("actions", [])
        if actions:
            await self._execute_actions(actions)

    @filter.command("sky_look")
    async def cmd_sky_look(self, event: AstrMessageEvent):
        """
        /sky_look - 让 AI 恋人描述当前游戏画面（用于调试）
        """
        if not self._is_master(event):
            return

        if not await self.sky.health_check():
            yield event.plain_result("⚠️ 连接不到游戏控制程序")
            return

        screenshot = await self.sky.screenshot()
        if not screenshot:
            yield event.plain_result("❌ 截图失败")
            return

        desc = await self.agent.look(screenshot)
        yield event.plain_result(f"👀 当前场景：\n{desc}")

    @filter.command("sky_key")
    async def cmd_sky_key(self, event: AstrMessageEvent):
        """
        /sky_key [按键] [时长ms] - 手动让 AI 恋人按键（调试用）
        例：/sky_key w 1000
        """
        if not self._is_master(event):
            return

        args = event.get_message_str().replace("/sky_key", "").strip().split()
        if not args:
            yield event.plain_result("用法：/sky_key [按键] [时长ms]\n例：/sky_key w 1000")
            return

        key = args[0]
        duration = int(args[1]) if len(args) > 1 else 80
        result = await self.sky.press_key(key, duration)
        yield event.plain_result(f"✅ {result}")

    @filter.command("sky_say")
    async def cmd_sky_say(self, event: AstrMessageEvent):
        """
        /sky_say [消息] - 让 AI 恋人在游戏内发送聊天消息
        """
        if not self._is_master(event):
            return

        msg = event.get_message_str().replace("/sky_say", "").strip()
        if not msg:
            yield event.plain_result("用法：/sky_say [消息内容]")
            return

        result = await self.sky.send_chat(msg)
        yield event.plain_result(f"💬 已发送：{msg}")

    @filter.command("sky_status")
    async def cmd_sky_status(self, event: AstrMessageEvent):
        """
        /sky_status - 查看连接状态
        """
        if not self._is_master(event):
            return

        name = self.cfg.get("lover_name", "AI恋人")
        model = self.cfg.get("ai_model", "未配置")
        alive = await self.sky.health_check()

        if alive:
            status = await self.sky.status()
            window = status.get("window")
            window_info = f"✅ 已找到（{window['title']}）" if window else "⚠️ 未找到游戏窗口"
            yield event.plain_result(
                f"💕 {name} 状态\n"
                f"📡 游戏控制：已连接\n"
                f"🎮 游戏窗口：{window_info}\n"
                f"🤖 模型：{model}\n\n"
                f"可用命令：\n"
                f"/sky [消息] - 让她回应并操作游戏\n"
                f"/sky_look - 看当前游戏画面\n"
                f"/sky_say [文字] - 在游戏内说话\n"
                f"/sky_key [按键] [时长] - 手动按键"
            )
        else:
            yield event.plain_result(
                f"💔 {name} 还没准备好\n"
                f"📡 游戏控制：未连接\n\n"
                f"请先在 Windows 上启动：\n"
                f"1. sky-mcp-server（start-http.bat）\n"
                f"2. frp 内网穿透"
            )
