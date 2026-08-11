"""Standalone SHADOW agent configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "shadow_config.yaml"


@dataclass
class ShadowConfig:
    permission: str = "always ask"  # "always ask" | "trusted"
    max_tokens: int = 0       # 0 = unlimited
    max_turns: int = 0        # 0 = unlimited
    stop_ratio: float = 0.00  # 0.00 = ratio stop disabled


CURRENT_CONFIG = ShadowConfig()


def save_config(cfg: ShadowConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        f"permission: {cfg.permission}\n"
        f"max_tokens: {cfg.max_tokens}\n"
        f"max_turns: {cfg.max_turns}\n"
        f"stop_ratio: {cfg.stop_ratio:.2f}\n"
    )