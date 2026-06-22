"""CFIRE 艺人内容策划技能

生成人物当天主要活动的选题策划和拍摄脚本，保存到 assets/content_draft/ 目录。
选题策划符合人物设定和世界观，偶尔与之前发布的内容做呼应。
拍摄脚本遵循标准格式：镜头、人物、音色、景别、光线、音效、画面、台词。
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from _common import CfireSkillBase


class CfireContentDraftSkill(CfireSkillBase):
    """CFIRE 艺人内容策划技能类"""

    DRAFT_DIR_NAME = "content_draft"
    CONTENT_PILLARS = {
        "日常陪伴", "创作进展", "粉丝互动", "独立态度",
        "活动预热", "活动复盘",
    }
    REQUIRED_SECTIONS = ("## 日期", "## 选题策划", "## 拍摄脚本")
    OPTIONAL_SECTIONS = ("## 角色妆造",)
    SHOT_FIELDS = ("景别", "光线", "音效", "画面")
    COSTUME_FIELDS = ("Cosplay 角色", "选择理由", "服装", "妆容")

    def __init__(self, profile_dir: Optional[Path] = None):
        super().__init__(profile_dir=profile_dir, skill_name="cfire_content_draft")
        self.draft_dir = self.assets_dir / self.DRAFT_DIR_NAME
        self.draft_dir.mkdir(parents=True, exist_ok=True)

    def build_prompt(self, context: Dict[str, Any], target_date: str) -> str:
        """构建内容策划生成提示词，包含选题策划和拍摄脚本两部分。"""
        files = context["files"]
        recent = context["recent"]

        event_lines = self._format_recent_events(recent)
        memory_lines = self._format_important_memories(recent)

        prompt = f"""你是艺人的内容策划助手。请根据以下人物设定、阶段目标与近期经历，为 {target_date} 生成一份内容策划，包含「选题策划」和「拍摄脚本」两部分。

【输出格式要求】
严格按以下 Markdown 结构输出，不要添加额外解释或代码块包裹：

# 内容策划 / {target_date}

## 日期
{target_date}

## 选题策划

### 选题名称
<一句话选题名称>

### 内容支柱
<从以下选择一个：日常陪伴 / 创作进展 / 粉丝互动 / 独立态度 / 活动预热 / 活动复盘>

### 主题描述
<2-4 句话描述选题主题，需符合人物设定和世界观，说明今天主要活动的内容方向>

### 与过往内容的呼应
<描述与最近内容的连续性；如无呼应则写"无">

### 预期情绪价值
<一句话说明希望给粉丝带来的情绪价值>

## 角色妆造（如选题涉及 Cosplay 或特定造型，请填写）

### Cosplay 角色
<角色名称及作品出处，如 珊瑚宫心海（原神）>

### 选择理由
<2-4 条 bullet，说明角色与今日主题、艺人气质的契合点>

### 服装
<详细穿搭描述，含上衣、下装、配饰、假发、鞋履>

### 妆容
<底妆、眼妆、唇妆、细节点缀>

### 场景搭配
<道具、布景、色调呼应建议>

## 拍摄脚本

[镜头 1]
【人物 1】<人物描述，含穿搭/妆造、场景、动作>
人物音色参考：<音频参考，如【音频 1】>
景别：<景别描述，如中景跟随拍摄、特写、远景固定>
光线：<光线描述，如室内柔和自然光、傍晚逆光>
音效：<音效描述，如只保留人声和环境音、轻量背景音乐>
画面：<画面描述，镜头运动和画面切换>
人物台词：<台词内容，注明语言，如（标准美式英语）：...>

[镜头 2]
<同上格式>

## 元信息
- 镜头数：<N>
- 保存时间：<留空，保存时自动填写>

【创作约束】
1. 选题必须符合艺人的独立音乐人人设：温柔、克制、清醒、有创作锋芒。
2. 优先延续最近 3-7 天时间线；可以偶尔与之前内容呼应，但不要强行重复。
3. 不编造未确认事实、未公开合作、未来活动或线下见面。
4. 拍摄脚本至少包含 2 个镜头，每个镜头必须包含：景别、光线、音效、画面、人物台词。
5. 如选题涉及 Cosplay，必须在「角色妆造」章节详细说明角色选择理由、服装、妆容和场景搭配；拍摄脚本的人物描述需呼应妆造细节。
6. 台词可中可英，英语台词需注明（标准美式英语）。

【短视频制作技巧——三幕结构】
拍摄脚本需遵循以下短视频叙事结构，确保内容在开头即抓住注意力：

**第 1 幕（黄金 3 秒）：抛出「情绪钩子」或「未完成的悬念」**
- 绝对不要用"大家好""我是..."这类平淡开场。
- 必须用一句对话、一个特写动作或一句内心独白直接切入情绪核心。
- 钩子原则：让观众在 3 秒内产生"后来呢？"的好奇，或"我也是"的共鸣。

**第 2 幕（中段展开）：用具体细节推进情绪**
- 通过动作、环境音、微表情让情绪落地，避免空泛抒情。
- 用"展示"代替"告诉"：不说"我很纠结"，而展示反复切换两个音频波形、指尖悬在琴键上方迟迟不落。
- 中段可加入一个"小转折"或"新发现"，保持节奏不塌陷。

**第 3 幕（结尾收束）：留白或向前的力量**
- 不强行总结道理，用一句轻量但有余味的台词收尾。
- 结尾可保留"未完成感"，或给出一个温柔的前行动作。
- 最后 1 秒的画面建议：人物低头微笑、望向窗外、或手指终于落下琴键——让观众带着画面离开。

【人物设定】
{files.get('identity', '')[:800]}

【性格与价值观】
{files.get('soul', '')[:800]}

【阶段目标】
{files.get('goals', '')[:600]}

【表达风格】
{files.get('voice_style', '')[:800]}

【内容策略】
{files.get('content_strategy', '')[:600]}

【安全边界】
{files.get('boundaries', '')[:400]}

【近期时间线】
{chr(10).join(event_lines) if event_lines else '（暂无）'}

【重要记忆】
{chr(10).join(memory_lines) if memory_lines else '（暂无）'}
"""
        return prompt

    def generate(
        self,
        target_date: Optional[str] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """生成内容策划。若配置 LLM 则自动产出，否则返回 prompt。"""
        target = target_date or date.today().isoformat()
        self._validate_date(target)
        context = self._load_context()
        prompt = self.build_prompt(context, target)
        content = ""
        source = "prompt"
        if use_llm:
            raw = self._call_llm(prompt, max_tokens=1500, temperature=0.85)
            if raw:
                content = self._clean_output(raw)
                source = "llm"
        if not content:
            return {
                "date": target, "content": "", "source": source,
                "prompt": prompt, "saved": False,
                "error": "未配置 LLM 或生成失败，已返回 prompt，可人工填写后调用 save。",
            }
        return {
            "date": target, "content": content, "source": source,
            "prompt": prompt, "saved": False,
        }

    def validate(self, content: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """按内容策划 Schema 校验。"""
        target = self._validate_date(target_date or date.today().isoformat())
        content = (content or "").strip()
        if not content:
            raise ValueError("内容策划正文不能为空")

        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                raise ValueError(f"内容策划缺少必需章节: {section}")

        content_date_match = re.search(r"## 日期\s*\n(\d{4}-\d{2}-\d{2})", content)
        if not content_date_match:
            raise ValueError("## 日期 章节格式错误，需为 YYYY-MM-DD")
        if content_date_match.group(1) != target:
            raise ValueError(
                f"文件日期 {content_date_match.group(1)} 与目标日期 {target} 不一致"
            )

        pillar_match = re.search(r"### 内容支柱\s*\n([^\n]+)", content)
        if pillar_match:
            pillar = pillar_match.group(1).strip()
            if pillar not in self.CONTENT_PILLARS:
                raise ValueError(
                    f"内容支柱 '{pillar}' 不在允许列表中，允许: {sorted(self.CONTENT_PILLARS)}"
                )

        shot_count = len(re.findall(r"\[镜头 \d+\]", content))
        if shot_count < 2:
            raise ValueError(f"拍摄脚本至少需要 2 个镜头，当前: {shot_count}")

        for field in self.SHOT_FIELDS:
            if field + "：" not in content:
                raise ValueError(f"拍摄脚本缺少必需字段: {field}：")

        result = {
            "date": target, "content": content,
            "shot_count": shot_count, "length": len(content),
            "has_costume": "## 角色妆造" in content,
        }

        # 如包含角色妆造章节，校验关键字段完整性（宽松校验，允许部分缺失）
        if result["has_costume"]:
            costume_checks = {}
            for field in self.COSTUME_FIELDS:
                costume_checks[field] = field in content
            result["costume_fields"] = costume_checks

        return result

    def _file_path_for(self, target_date: str) -> Path:
        return self.draft_dir / f"{target_date}.md"

    def _render_draft_file(self, target_date: str, content: str) -> str:
        """渲染最终文件内容，自动补充元信息。"""
        shot_count = len(re.findall(r"\[镜头 \d+\]", content))
        saved_at = datetime.now().replace(microsecond=0).isoformat()

        if "## 元信息" in content:
            content = re.sub(
                r"## 元信息[\s\S]*$",
                f"## 元信息\n- 镜头数：{shot_count}\n- 保存时间：{saved_at}\n",
                content,
            )
        else:
            content = content.rstrip() + f"\n\n## 元信息\n- 镜头数：{shot_count}\n- 保存时间：{saved_at}\n"
        return content

    def _parse_draft_file(self, path: Path) -> Dict[str, Any]:
        """解析内容策划文件，提取关键字段。"""
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

        for key in ("日期", "选题策划", "拍摄脚本"):
            if key not in sections:
                raise ValueError(f"内容策划文件缺少必需章节: ## {key}")

        shot_count = len(re.findall(r"\[镜头 \d+\]", sections.get("拍摄脚本", "")))
        result = {
            "date": sections["日期"],
            "topic_planning": sections["选题策划"],
            "shooting_script": sections["拍摄脚本"],
            "shot_count": shot_count,
            "length": len(text),
            "path": str(path),
            "has_costume": "角色妆造" in sections,
        }
        if result["has_costume"]:
            result["costume"] = sections.get("角色妆造", "")
        return result

    def save(self, content: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """按 Schema 保存内容策划：独立 Markdown 文件 + memory_store 时间线。"""
        validated = self.validate(content=content, target_date=target_date)
        target = validated["date"]
        rendered = self._render_draft_file(target, validated["content"])

        path = self._file_path_for(target)
        path.write_text(rendered, encoding="utf-8")

        from memory_store import init, repository
        init()
        topic_match = re.search(r"### 选题名称\s*\n([^\n]+)", validated["content"])
        topic_name = topic_match.group(1).strip() if topic_match else "内容策划"
        event_id = repository.save_timeline_event(
            event_date=target,
            event_type="创作",
            content=f"内容策划：{topic_name}",
            mood="",
            extendable_content=f"拍摄脚本 {validated['shot_count']} 个镜头，可作为发布内容的参考",
        )

        self.logger.info(
            f"内容策划已保存: date={target}, event_id={event_id}, shots={validated['shot_count']}"
        )
        return {
            "date": target, "content": rendered,
            "shot_count": validated["shot_count"],
            "length": len(rendered), "event_id": event_id,
            "draft_path": str(path), "saved": True,
        }

    def read(self, target_date: str) -> Dict[str, Any]:
        """读取指定日期的内容策划文件。"""
        target = self._validate_date(target_date)
        path = self._file_path_for(target)
        if not path.exists():
            raise FileNotFoundError(f"内容策划文件不存在: {path}")
        return self._parse_draft_file(path)

    def list_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出 content_draft/ 目录下最近的内容策划文件。"""
        if not self.draft_dir.exists():
            return []
        paths = sorted(self.draft_dir.glob("????-??-??.md"), reverse=True)[:limit]
        items: List[Dict[str, Any]] = []
        for p in paths:
            try:
                items.append(self._parse_draft_file(p))
            except ValueError as e:
                self.logger.warning(f"解析内容策划失败 {p}: {e}")
        return items
