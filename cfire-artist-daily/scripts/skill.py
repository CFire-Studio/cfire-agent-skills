"""CFIRE 艺人日记与内容策划技能

参考人物设定、目标与过往经历生成每日日记与内容策划（选题 + 拍摄脚本），
并持久化到对应目录与 memory_store，作为后续内容生成的上下文参考。
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from _common import CfireSkillBase
from content_draft import CfireContentDraftSkill


class CfireArtistDailySkill(CfireSkillBase):
    """CFIRE 艺人日记更新技能类"""

    MAX_DIARY_LENGTH = 200
    DIARY_DIR_NAME = "diary"
    MOOD_ALLOWED = {"开心", "期待", "紧张", "疲惫", "温柔", "平静", "焦虑", "安心", "兴奋", "迷茫"}
    REQUIRED_SECTIONS = ("## 正文", "## 情绪")

    def __init__(self, profile_dir: Optional[Path] = None):
        super().__init__(profile_dir=profile_dir, skill_name="cfire_artist_daily")
        self.diary_dir = self.assets_dir / self.DIARY_DIR_NAME
        self.diary_dir.mkdir(parents=True, exist_ok=True)

    def build_prompt(self, context: Dict[str, Any], target_date: str) -> str:
        """根据人物设定、目标与过往经历构建日记生成提示词。"""
        files = context["files"]
        recent = context["recent"]

        event_lines = self._format_recent_events(recent)
        memory_lines = self._format_important_memories(recent)

        prompt = f"""你是艺人。请根据以下人物设定、阶段目标与近期经历，以第一人称撰写 {target_date} 的日常动态文本。

写作要求：
1. 描述今天做了什么、看到/听到/遇到什么有趣的小事、自己的心情与感受。
2. 内容要适合直接作为社交媒体动态发布，自然流畅，有画面感和真实感。
3. 严格遵循人物设定、语气风格与安全边界，不编造未确认事实、未公开合作或未来活动。
4. 正文长度不超过 200 字（含标点与空格）。
5. 用第一人称，语气温柔、克制、清醒，可带轻微诗性，不卖惨、不硬广。
6. 直接输出正文内容，不要加标题、日期、前缀、解释或引号。

【人物设定】
{files.get('identity', '')[:800]}

【性格与价值观】
{files.get('soul', '')[:800]}

【阶段目标】
{files.get('goals', '')[:800]}

【表达风格】
{files.get('voice_style', '')[:600]}

【安全边界】
{files.get('boundaries', '')[:400]}

【近期时间线】
{chr(10).join(event_lines) if event_lines else '（暂无）'}

【重要记忆】
{chr(10).join(memory_lines) if memory_lines else '（暂无）'}
"""
        return prompt

    def _truncate_to_limit(self, text: str) -> str:
        """在长度限制内，优先在句尾截断。"""
        if len(text) <= self.MAX_DIARY_LENGTH:
            return text
        truncated = text[: self.MAX_DIARY_LENGTH]
        for sep in ["\n", "。", "！", "？", "；"]:
            idx = truncated.rfind(sep)
            if idx > self.MAX_DIARY_LENGTH * 0.5:
                truncated = truncated[: idx + 1]
                break
        return truncated.strip()[: self.MAX_DIARY_LENGTH]

    @staticmethod
    def _validate_mood(mood: str) -> str:
        mood = (mood or "").strip()
        if not mood:
            return "平静"
        if mood not in CfireArtistDailySkill.MOOD_ALLOWED:
            raise ValueError(
                f"情绪标签 '{mood}' 不在允许列表中，允许: "
                f"{sorted(CfireArtistDailySkill.MOOD_ALLOWED)}"
            )
        return mood

    @staticmethod
    def _validate_content(content: str) -> str:
        content = (content or "").strip()
        if not content:
            raise ValueError("日记正文不能为空")
        if len(content) > CfireArtistDailySkill.MAX_DIARY_LENGTH:
            raise ValueError(
                f"日记正文长度 {len(content)} 超过 "
                f"{CfireArtistDailySkill.MAX_DIARY_LENGTH} 字限制"
            )
        return content

    def _file_path_for(self, target_date: str) -> Path:
        return self.diary_dir / f"{target_date}.md"

    def _render_diary_file(self, target_date: str, content: str, mood: str) -> str:
        from datetime import datetime
        saved_at = datetime.now().replace(microsecond=0).isoformat()
        return (
            f"# 日记 / {target_date}\n"
            "\n"
            "## 正文\n"
            f"{content}\n"
            "\n"
            "## 情绪\n"
            f"{mood}\n"
            "\n"
            "## 元信息\n"
            f"- 日期：{target_date}\n"
            f"- 字数：{len(content)}\n"
            f"- 保存时间：{saved_at}\n"
        )

    def _parse_diary_file(self, path: Path) -> Dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        sections: Dict[str, str] = {}
        current = None
        buf: List[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                if current:
                    sections[current] = "\n".join(buf).strip()
                current = line[3:].strip()
                buf = []
                continue
            if current is not None and not line.startswith("# "):
                buf.append(line)
        if current:
            sections[current] = "\n".join(buf).strip()

        for key in ("正文", "情绪"):
            if key not in sections:
                raise ValueError(f"日记文件缺少必需章节: ## {key}")

        # 从文件名或元信息中提取日期
        date_from_file = path.stem
        # 从元信息中提取日期（如果存在）
        date_from_meta = date_from_file
        if "元信息" in sections:
            for line in sections["元信息"].splitlines():
                if line.startswith("- 日期："):
                    date_from_meta = line[len("- 日期："):].strip()

        return {
            "date": date_from_meta,
            "mood": sections["情绪"],
            "content": sections["正文"],
            "length": len(sections["正文"]),
            "path": str(path),
        }

    def validate(self, content: str, target_date: Optional[str] = None,
                 mood: Optional[str] = None) -> Dict[str, Any]:
        """按独立 Schema 校验日记元数据与正文。"""
        target = self._validate_date(target_date or date.today().isoformat())
        mood = self._validate_mood(mood or self._extract_mood(content))
        content = self._validate_content(content)
        return {"date": target, "mood": mood, "content": content, "length": len(content)}

    def read(self, target_date: str) -> Dict[str, Any]:
        """读取指定日期的日记文件。"""
        target = self._validate_date(target_date)
        path = self._file_path_for(target)
        if not path.exists():
            raise FileNotFoundError(f"日记文件不存在: {path}")
        return self._parse_diary_file(path)

    def generate(
        self,
        target_date: Optional[str] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """生成日记。若配置 LLM 则自动产出正文，否则返回 prompt。"""
        target = target_date or date.today().isoformat()
        context = self._load_context()
        prompt = self.build_prompt(context, target)
        content = ""
        source = "prompt"
        if use_llm:
            raw = self._call_llm(prompt, max_tokens=300, temperature=0.8)
            if raw:
                content = self._truncate_to_limit(self._clean_output(raw))
                source = "llm"
        if not content:
            return {"date": target, "content": "", "source": source,
                    "prompt": prompt, "saved": False,
                    "error": "未配置 LLM 或生成失败，已返回 prompt，可人工填写后调用 save。"}
        return {"date": target, "content": content, "mood": self._extract_mood(content),
                "length": len(content), "source": source, "prompt": prompt, "saved": False}

    def _extract_mood(self, text: str) -> str:
        """基于简单关键词提取情绪标签，优先返回允许列表中的值。"""
        for keyword, mood in [
            ("开心", "开心"), ("期待", "期待"), ("紧张", "紧张"),
            ("累", "疲惫"), ("疲惫", "疲惫"), ("慢", "疲惫"),
            ("温柔", "温柔"), ("平静", "平静"), ("慌", "焦虑"),
            ("安心", "安心"), ("亮", "期待"), ("冒险", "兴奋"), ("迷茫", "迷茫"),
        ]:
            if keyword in text:
                return mood
        return "平静"

    def save(
        self,
        content: str,
        target_date: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按独立 Schema 保存日记：独立 Markdown 文件 + memory_store 时间线事件。"""
        validated = self.validate(content=content, target_date=target_date, mood=mood)
        target = validated["date"]
        content = validated["content"]
        mood = validated["mood"]

        path = self._file_path_for(target)
        path.write_text(self._render_diary_file(target, content, mood), encoding="utf-8")

        from memory_store import init, repository
        init()
        event_id = repository.save_timeline_event(
            event_date=target, event_type="日记", content=content, mood=mood,
            extendable_content="可作为后续日常动态、创作手记与粉丝互动的参考",
        )

        self.logger.info(f"日记已保存: date={target}, event_id={event_id}, length={len(content)}")
        return {
            "date": target, "content": content, "mood": mood, "length": len(content),
            "event_id": event_id, "diary_path": str(path), "saved": True,
        }

    def list_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出 diary/ 目录下最近的日记文件。"""
        if not self.diary_dir.exists():
            return []
        paths = sorted(self.diary_dir.glob("????-??-??.md"), reverse=True)[:limit]
        items: List[Dict[str, Any]] = []
        for p in paths:
            try:
                items.append(self._parse_diary_file(p))
            except ValueError as e:
                self.logger.warning(f"解析日记失败 {p}: {e}")
        return items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CFIRE 艺人日记与内容策划 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 日记命令
    gen = sub.add_parser("generate", help="生成日记（自动或输出 prompt）")
    gen.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    gen.add_argument("--date", "-d", help="日记日期，默认今天（YYYY-MM-DD）")
    gen.add_argument("--no-llm", action="store_true", help="不调用 LLM，仅输出生成 prompt")
    gen.add_argument("--save", action="store_true", help="生成成功后立即保存")

    save = sub.add_parser("save", help="保存已有的日记内容")
    save.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    save.add_argument("--date", "-d", help="日记日期，默认今天（YYYY-MM-DD）")
    save.add_argument("--mood", "-m", help="情绪标签，默认自动提取")
    save.add_argument("--content", "-c", required=True, help="日记正文（不超过 200 字）")

    read_cmd = sub.add_parser("read", help="读取指定日期的日记文件")
    read_cmd.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    read_cmd.add_argument("--date", "-d", required=True, help="日记日期（YYYY-MM-DD）")

    validate_cmd = sub.add_parser("validate", help="校验日记是否符合独立存储 Schema")
    validate_cmd.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    validate_cmd.add_argument("--date", "-d", help="日记日期，默认今天（YYYY-MM-DD）")
    validate_cmd.add_argument("--mood", "-m", help="情绪标签")
    validate_cmd.add_argument("--content", "-c", required=True, help="日记正文")

    list_cmd = sub.add_parser("list", help="列出最近日记")
    list_cmd.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    list_cmd.add_argument("--limit", "-n", type=int, default=10, help="返回数量")

    # 内容策划命令
    draft_gen = sub.add_parser("draft-generate", help="生成内容策划（选题 + 拍摄脚本）")
    draft_gen.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    draft_gen.add_argument("--date", "-d", help="策划日期，默认今天（YYYY-MM-DD）")
    draft_gen.add_argument("--no-llm", action="store_true", help="不调用 LLM，仅输出生成 prompt")
    draft_gen.add_argument("--save", action="store_true", help="生成成功后立即保存")

    draft_save = sub.add_parser("draft-save", help="保存已有的内容策划")
    draft_save.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    draft_save.add_argument("--date", "-d", help="策划日期，默认今天（YYYY-MM-DD）")
    draft_save.add_argument("--content", "-c", required=True, help="内容策划正文（Markdown）")

    draft_read = sub.add_parser("draft-read", help="读取指定日期的内容策划")
    draft_read.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    draft_read.add_argument("--date", "-d", required=True, help="策划日期（YYYY-MM-DD）")

    draft_list = sub.add_parser("draft-list", help="列出最近内容策划")
    draft_list.add_argument("--profile-dir", "-p", help="cfire-artist-profile 目录路径")
    draft_list.add_argument("--limit", "-n", type=int, default=10, help="返回数量")

    return parser


def _run_diary_cmd(args, skill: CfireArtistDailySkill) -> None:
    """执行日记子命令。"""
    if args.cmd == "generate":
        result = skill.generate(target_date=args.date, use_llm=not args.no_llm)
        if result.get("content") and args.save:
            result.update(skill.save(content=result["content"], target_date=result["date"],
                                       mood=result.get("mood")))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "save":
        print(json.dumps(skill.save(content=args.content, target_date=args.date,
                                      mood=args.mood), ensure_ascii=False, indent=2))
    elif args.cmd == "read":
        print(json.dumps(skill.read(args.date), ensure_ascii=False, indent=2))
    elif args.cmd == "validate":
        print(json.dumps(skill.validate(content=args.content, target_date=args.date,
                                          mood=args.mood), ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        items = skill.list_files(limit=args.limit)
        print(json.dumps({"items": items, "source": "diary_dir"}, ensure_ascii=False, indent=2))


def _run_draft_cmd(args, skill: CfireContentDraftSkill) -> None:
    """执行内容策划子命令。"""
    if args.cmd == "draft-generate":
        result = skill.generate(target_date=args.date, use_llm=not args.no_llm)
        if result.get("content") and args.save:
            result.update(skill.save(content=result["content"], target_date=result["date"]))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "draft-save":
        print(json.dumps(skill.save(content=args.content, target_date=args.date),
                          ensure_ascii=False, indent=2))
    elif args.cmd == "draft-read":
        print(json.dumps(skill.read(args.date), ensure_ascii=False, indent=2))
    elif args.cmd == "draft-list":
        items = skill.list_files(limit=args.limit)
        print(json.dumps({"items": items, "source": "content_draft_dir"},
                          ensure_ascii=False, indent=2))


def _main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    draft_cmds = {"draft-generate", "draft-save", "draft-read", "draft-list"}
    try:
        if args.cmd in draft_cmds:
            skill = CfireContentDraftSkill(profile_dir=getattr(args, "profile_dir", None))
            _run_draft_cmd(args, skill)
        else:
            skill = CfireArtistDailySkill(profile_dir=getattr(args, "profile_dir", None))
            _run_diary_cmd(args, skill)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
