"""CFIRE 艺人技能共享模块

提供艺人技能通用的基础能力：档案目录解析、日志、LLM 调用、上下文加载等。
日记、内容策划等具体技能继承本基类，复用通用逻辑。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class CfireSkillBase:
    """CFIRE 艺人技能基类，封装通用能力。"""

    PROFILE_DIR_NAME = "cfire-artist-profile"
    REFERENCE_FILES = [
        "IDENTITY.md",
        "SOUL.md",
        "GOALS.md",
        "VOICE_STYLE.md",
        "CONTENT_STRATEGY.md",
        "BOUNDARIES.md",
        "MEMORY.md",
        "TIMELINE.md",
        "SCHEDULE.md",
    ]

    def __init__(self, profile_dir: Optional[Path] = None, skill_name: str = "cfire_skill"):
        self.profile_dir = self._resolve_profile_dir(profile_dir)
        self.reference_dir = self.profile_dir / "reference"
        skill_dir = Path(__file__).parent.parent.resolve()
        self.assets_dir = skill_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_memory_store_importable()
        self.logger = self._setup_logging(skill_name)

    def _resolve_profile_dir(self, profile_dir: Optional[Path]) -> Path:
        """解析艺人档案目录，支持显式传入或自动发现同级 cfire-artist-profile。"""
        if profile_dir:
            resolved = Path(profile_dir).resolve()
            if not resolved.is_dir():
                raise NotADirectoryError(f"档案目录不存在: {resolved}")
            return resolved

        start = Path(__file__).parent.resolve()
        sibling = start.parent.parent / self.PROFILE_DIR_NAME
        if sibling.is_dir():
            return sibling

        for path in [start, *start.parents]:
            candidate = path / self.PROFILE_DIR_NAME
            if candidate.is_dir():
                return candidate

        raise FileNotFoundError(
            f"未找到 {self.PROFILE_DIR_NAME} 目录，请使用 --profile-dir 显式指定。"
        )

    def _ensure_memory_store_importable(self) -> None:
        """将 cfire-artist-profile 加入模块搜索路径，以便复用 memory_store。"""
        profile_str = str(self.profile_dir)
        if profile_str not in sys.path:
            sys.path.insert(0, profile_str)

    def _setup_logging(self, skill_name: str) -> logging.Logger:
        """初始化日志，写入 scripts/logs/skill.log。"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        logger = logging.getLogger(skill_name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            fh = logging.FileHandler(log_dir / "skill.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        return logger

    def _read_reference(self, filename: str) -> str:
        """读取 reference 目录下的 Markdown 配置文件。"""
        path = self.reference_dir / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _load_context(self, days: int = 7) -> Dict[str, Any]:
        """加载档案文件与近期记忆上下文。"""
        from memory_store import init, search

        init()
        recent = search.get_recent_context(days=days, limit=15)

        files: Dict[str, str] = {}
        for filename in self.REFERENCE_FILES:
            key = filename.replace(".md", "").lower()
            files[key] = self._read_reference(filename)

        return {"files": files, "recent": recent}

    def _call_llm(self, prompt: str, max_tokens: int = 800, temperature: float = 0.8) -> Optional[str]:
        """若环境变量配置 LLM，则调用大模型生成内容；否则返回 None。"""
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()
        provider = os.getenv("LLM_PROVIDER", "volcengine").strip().lower()
        if not api_key or not model:
            return None
        if provider != "volcengine":
            self.logger.warning(f"不支持的 LLM 提供商: {provider}，跳过自动生成")
            return None
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            self.logger.error(f"LLM 调用失败: {e}")
            return None

    @staticmethod
    def _clean_output(text: str) -> str:
        """清理模型输出中的代码块、引号与多余空白。"""
        text = text.strip().strip('"').strip("'")
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                first, rest = text.split("\n", 1)
                if first.strip().lower() in {"markdown", "text", "diary", "json", ""}:
                    text = rest
        return text.strip()

    @staticmethod
    def _validate_date(target_date: str) -> str:
        from datetime import datetime
        try:
            d = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"日期格式无效: {target_date}，必须为 YYYY-MM-DD") from e
        if d.year < 2000 or d.year > 2100:
            raise ValueError(f"日期超出合理范围: {target_date}")
        return target_date

    def _format_recent_events(self, recent: Dict[str, Any]) -> List[str]:
        """格式化近期事件为字符串列表。"""
        recent_events = recent.get("recent_events", [])
        return [
            f"- {e['event_date']} [{e['event_type']}] {e['content']}"
            for e in recent_events
        ]

    def _format_important_memories(self, recent: Dict[str, Any]) -> List[str]:
        """格式化重要记忆为字符串列表。"""
        important_memories = recent.get("important_memories", [])
        return [f"- {m['content']}" for m in important_memories]
