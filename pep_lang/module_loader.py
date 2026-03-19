from __future__ import annotations

from typing import Any, Optional

from pep_lang.libs.discord import DiscordLibrary
from pep_lang.libs.discord_beta import DiscordBeta


class ModuleLoadError(Exception):
    pass


def load_module(module: str, version: Optional[str] = None) -> Any:
    normalized = module.strip().lower()

    if normalized == "discord":
        if version in {"beta", "0.1", "0.1.0-beta"}:
            return DiscordBeta()
        if version and version not in {"stable", "1", "1.0", "1.0.0"}:
            raise ModuleLoadError(
                f"Unsupported discord version '{version}'. Use stable|1.0.0 or beta."
            )
        return DiscordLibrary()

    raise ModuleLoadError(f"Unknown module: {module}")
