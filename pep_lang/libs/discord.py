from __future__ import annotations

import asyncio
import queue
import threading
from typing import Any, Dict, List, Optional


class DiscordLibraryError(Exception):
    pass


class DiscordLibrary:
    """Discord integration for pep#.

    Features:
    - Real bot connection with discord.py
    - Prefix commands with static replies
    - Message capture queue (read user messages)
    - Send text/embed to channels
    - Blocking or background run modes
    """

    version = "1.0.0"

    def __init__(self) -> None:
        self._discord = self._import_discord()
        self._commands_ext = self._discord.ext.commands

        self._token: Optional[str] = None
        self._prefix: str = "!"
        self._bot: Any = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._messages: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._message_snapshot: List[Dict[str, Any]] = []
        self._keyword_replies: List[tuple[str, str]] = []
        self._registered_commands: Dict[str, str] = {}

    @staticmethod
    def _import_discord():
        try:
            import discord  # type: ignore
            from discord.ext import commands  # type: ignore

            discord.ext = type("ext", (), {"commands": commands})
            return discord
        except Exception as exc:  # noqa: BLE001
            raise DiscordLibraryError(
                "discord.py is not installed. Run: pip install discord.py"
            ) from exc

    def info(self) -> Dict[str, Any]:
        return {
            "name": "discord",
            "channel": "stable",
            "version": self.version,
            "connected": bool(self._bot and not self._bot.is_closed()),
            "prefix": self._prefix,
            "commands": list(self._registered_commands.keys()),
        }

    def bot(self, token: str, prefix: str = "!") -> Dict[str, Any]:
        self._token = token
        self._prefix = prefix
        self._ensure_bot()
        return {
            "ok": True,
            "message": "bot configured",
            "prefix": self._prefix,
        }

    def command(self, name: str, response: str) -> Dict[str, Any]:
        bot = self._ensure_bot()
        command_name = name.strip().lower()
        if not command_name:
            raise DiscordLibraryError("command name cannot be empty")

        async def _handler(ctx):
            await ctx.send(response)

        bot.command(name=command_name)(_handler)
        self._registered_commands[command_name] = response
        return {"ok": True, "message": f"command '{command_name}' registered"}

    def command_embed(
        self,
        name: str,
        title: str,
        description: str,
        color: int = 0x00D4A5,
    ) -> Dict[str, Any]:
        bot = self._ensure_bot()
        command_name = name.strip().lower()
        if not command_name:
            raise DiscordLibraryError("command name cannot be empty")

        async def _handler(ctx):
            rich = self._discord.Embed(
                title=title,
                description=description,
                color=int(color),
            )
            await ctx.send(embed=rich)

        bot.command(name=command_name)(_handler)
        self._registered_commands[command_name] = f"embed:{title}"
        return {"ok": True, "message": f"embed command '{command_name}' registered"}

    def on_message_contains(self, keyword: str, response: str) -> Dict[str, Any]:
        key = keyword.strip().lower()
        if not key:
            raise DiscordLibraryError("keyword cannot be empty")
        self._keyword_replies.append((key, response))
        self._ensure_bot()
        return {"ok": True, "message": f"keyword reply '{key}' registered"}

    def start(self) -> None:
        if not self._token:
            raise DiscordLibraryError("token is required. Call discord.bot(token, prefix)")
        bot = self._ensure_bot()
        bot.run(self._token)

    def start_background(self) -> Dict[str, Any]:
        if not self._token:
            raise DiscordLibraryError("token is required. Call discord.bot(token, prefix)")
        if self._thread and self._thread.is_alive():
            return {"ok": True, "message": "bot already running in background"}

        def _run() -> None:
            self.start()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return {"ok": True, "message": "bot started in background"}

    def stop(self) -> Dict[str, Any]:
        if not self._bot:
            return {"ok": True, "message": "bot is not running"}

        if self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._bot.close(), self._loop)
            fut.result(timeout=10)
            return {"ok": True, "message": "bot stopped"}

        return {"ok": True, "message": "bot stop requested"}

    def send_channel(self, channel_id: int, content: str) -> Dict[str, Any]:
        async def _send() -> Dict[str, Any]:
            channel = self._bot.get_channel(int(channel_id))
            if channel is None:
                channel = await self._bot.fetch_channel(int(channel_id))
            await channel.send(content)
            return {"ok": True, "message": "sent"}

        return self._run_coro(_send())

    def embed(self, title: str, description: str, color: int = 0x00D4A5) -> Dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "color": int(color),
        }

    def send_embed_channel(self, channel_id: int, embed: Dict[str, Any]) -> Dict[str, Any]:
        async def _send() -> Dict[str, Any]:
            channel = self._bot.get_channel(int(channel_id))
            if channel is None:
                channel = await self._bot.fetch_channel(int(channel_id))

            rich = self._discord.Embed(
                title=embed.get("title", ""),
                description=embed.get("description", ""),
                color=int(embed.get("color", 0x00D4A5)),
            )
            await channel.send(embed=rich)
            return {"ok": True, "message": "embed sent"}

        return self._run_coro(_send())

    def next_message(self, timeout: float = 0.0) -> Dict[str, Any]:
        try:
            if timeout and timeout > 0:
                return self._messages.get(timeout=timeout)
            return self._messages.get_nowait()
        except queue.Empty:
            return {}

    def queued_messages(self) -> int:
        return self._messages.qsize()

    def recent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        n = max(1, int(limit))
        return self._message_snapshot[-n:]

    def mention_user(self, user_id: str) -> str:
        return f"<@{user_id}>"

    def mention_role(self, role_id: str) -> str:
        return f"<@&{role_id}>"

    def mention_channel(self, channel_id: str) -> str:
        return f"<#{channel_id}>"

    def _ensure_bot(self):
        if self._bot is not None:
            return self._bot

        intents = self._discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        bot = self._commands_ext.Bot(command_prefix=self._prefix, intents=intents)

        @bot.event
        async def on_ready():
            self._loop = asyncio.get_running_loop()

        @bot.event
        async def on_message(message):
            if message.author == bot.user:
                return

            payload = {
                "author_id": str(message.author.id),
                "author_name": str(message.author),
                "channel_id": str(message.channel.id),
                "content": message.content,
            }
            self._messages.put(payload)
            self._message_snapshot.append(payload)
            if len(self._message_snapshot) > 1000:
                self._message_snapshot = self._message_snapshot[-1000:]

            lowered = message.content.lower()
            for keyword, response in self._keyword_replies:
                if keyword in lowered:
                    await message.channel.send(response)

            await bot.process_commands(message)

        self._bot = bot
        return bot

    def _run_coro(self, coro):
        if not self._bot:
            raise DiscordLibraryError("bot is not configured")

        if self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=15)

        if self._token and not self._bot.is_ready():
            raise DiscordLibraryError("bot is not connected yet. Call start() or start_background()")

        return asyncio.run(coro)
