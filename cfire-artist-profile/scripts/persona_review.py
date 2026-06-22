"""
角色设定变更审查技能 - 核心实现

参考代码项目管理的 PR 审查流程，对智能体关键背景设定和经历变化进行变更检查
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ChangeSeverity(Enum):
    """变更严重程度"""
    BREAKING = "BREAKING"  # 破坏性变更
    HIGH = "HIGH"  # 高影响
    MEDIUM = "MEDIUM"  # 中等影响
    LOW = "LOW"  # 低影响
    NONE = "NONE"  # 无影响


class ChangeType(Enum):
    """变更类型"""
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"


@dataclass
class ChangeDiff:
    """单个变更的 diff 信息"""
    file_path: str
    section: str
    key: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: ChangeType = ChangeType.MODIFY


@dataclass
class ImpactAssessment:
    """变更影响评估"""
    affected_areas: List[str]
    risk_level: ChangeSeverity
    mitigation_suggestions: List[str]
    review_checklist: List[str]


class PersonaChangeReviewer:
    """角色设定变更审查器"""

    # 关键配置文件及其重要性
    CRITICAL_FILES = {
        "IDENTITY.md": {
            "severity": ChangeSeverity.BREAKING,
            "sections": ["基本资料", "公开人设", "世界观", "不可随意变更项"],
            "impact_areas": ["人设一致性", "粉丝认知", "内容生成", "历史内容回溯"]
        },
        "SOUL.md": {
            "severity": ChangeSeverity.HIGH,
            "sections": ["性格底色", "价值观", "主观偏好", "主动行为倾向"],
            "impact_areas": ["表达风格", "价值观一致性", "内容倾向", "互动方式"]
        },
        "MEMORY.md": {
            "severity": ChangeSeverity.HIGH,
            "sections": ["长期记忆"],
            "impact_areas": ["叙事连续性", "事实一致性"]
        },
        "TIMELINE.md": {
            "severity": ChangeSeverity.MEDIUM,
            "sections": ["近期事件"],
            "impact_areas": ["时间线连续性", "近期内容衔接"]
        },
        "VOICE_STYLE.md": {
            "severity": ChangeSeverity.MEDIUM,
            "sections": ["总体语气", "常用表达", "禁用表达", "场景语气"],
            "impact_areas": ["表达一致性"]
        },
        "GOALS.md": {
            "severity": ChangeSeverity.MEDIUM,
            "sections": ["长期目标", "当前阶段目标"],
            "impact_areas": ["内容方向", "策略一致性"]
        },
        "CONTENT_STRATEGY.md": {
            "severity": ChangeSeverity.LOW,
            "sections": ["内容支柱", "更新节奏", "平台差异"],
            "impact_areas": ["内容策略"]
        },
        "BOUNDARIES.md": {
            "severity": ChangeSeverity.BREAKING,
            "sections": ["绝对禁止", "必须人工确认", "粉丝关系边界"],
            "impact_areas": ["安全边界", "合规性"]
        },
        "FAN_RELATIONSHIP.md": {
            "severity": ChangeSeverity.MEDIUM,
            "sections": ["粉丝基础设定", "互动原则", "互动优先级"],
            "impact_areas": ["粉丝互动", "关系定位"]
        }
    }

    def __init__(self, profile_dir: Path):
        self.profile_dir = Path(profile_dir)
        self.reference_dir = self.profile_dir / "reference"

    def parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 Markdown 配置文件，提取章节和内容"""
        if not file_path.exists():
            return {}

        content = file_path.read_text(encoding="utf-8")
        result = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            # 检查标题行
            header_match = re.match(r"^##?\s+(.+)$", line)
            if header_match:
                if current_section:
                    result[current_section] = "\n".join(current_content).strip()
                current_section = header_match.group(1)
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            result[current_section] = "\n".join(current_content).strip()

        return result

    def compute_diff(self, old_content: Dict[str, Any], new_content: Dict[str, Any], file_name: str) -> List[ChangeDiff]:
        """计算两个内容字典之间的差异"""
        diffs = []
        all_sections = set(old_content.keys()) | set(new_content.keys())

        for section in all_sections:
            old_val = old_content.get(section, "")
            new_val = new_content.get(section, "")

            if old_val != new_val:
                if section not in old_content:
                    change_type = ChangeType.ADD
                elif section not in new_content:
                    change_type = ChangeType.DELETE
                else:
                    change_type = ChangeType.MODIFY

                diffs.append(ChangeDiff(
                    file_path=file_name,
                    section=section,
                    key=section,
                    old_value=old_val,
                    new_value=new_val,
                    change_type=change_type
                ))

        # 解析列表项级别的差异
        for section in old_content:
            if section in new_content:
                old_lines = self._parse_list_items(old_content[section])
                new_lines = self._parse_list_items(new_content[section])

                for key, old_val in old_lines.items():
                    if key in new_lines and old_val != new_lines[key]:
                        diffs.append(ChangeDiff(
                            file_path=file_name,
                            section=section,
                            key=key,
                            old_value=old_val,
                            new_value=new_lines[key],
                            change_type=ChangeType.MODIFY
                        ))

        return diffs

    def _parse_list_items(self, content: str) -> Dict[str, str]:
        """解析列表项为键值对"""
        items = {}
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            # 匹配 - 关键词：内容 或 - 关键词: 内容
            match = re.match(r"^[-*]\s*([^：:]+)[：:]\s*(.*)$", line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                items[key] = value

        return items

    def assess_impact(self, diffs: List[ChangeDiff]) -> ImpactAssessment:
        """评估变更的影响范围和风险等级"""
        affected_areas = set()
        risk_level = ChangeSeverity.NONE
        suggestions = []
        checklist = []

        for diff in diffs:
            file_config = self.CRITICAL_FILES.get(diff.file_path)
            if file_config:
                # 更新风险等级
                if file_config["severity"].value > risk_level.value:
                    risk_level = file_config["severity"]

                # 添加影响领域
                affected_areas.update(file_config["impact_areas"])

                # 检查是否修改了关键章节
                if diff.section in file_config["sections"]:
                    suggestions.append(f"关键章节变更：{diff.file_path} → {diff.section}")

                # 检查删除操作
                if diff.change_type == ChangeType.DELETE:
                    suggestions.append(f"删除操作需要特别审查：{diff.file_path} → {diff.section}")

        # 根据风险等级生成审查清单
        if risk_level in [ChangeSeverity.BREAKING, ChangeSeverity.HIGH]:
            checklist.extend([
                "确认变更有明确的业务需求或合理理由",
                "检查是否与现有记忆/时间线冲突",
                "评估对粉丝认知的影响",
                "检查历史内容是否需要回溯调整",
                "确认变更后的人设一致性",
                "安排过渡内容避免突兀变化",
                "记录变更原因和决策过程"
            ])
        elif risk_level == ChangeSeverity.MEDIUM:
            checklist.extend([
                "确认变更理由充分",
                "检查与近期内容的衔接",
                "验证人设一致性"
            ])

        return ImpactAssessment(
            affected_areas=sorted(list(affected_areas)),
            risk_level=risk_level,
            mitigation_suggestions=suggestions,
            review_checklist=checklist
        )

    def review_changes(self, old_dir: Optional[Path] = None, new_files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        执行完整的变更审查流程

        参数:
            old_dir: 旧版本目录（可选，用于与当前版本对比）
            new_files: 新文件内容字典 {文件名: 内容}（可选，用于与当前版本对比）

        返回:
            完整的审查报告
        """
        all_diffs = []
        files_changed = []

        # 确定要对比的文件
        if old_dir:
            # 对比目录
            old_ref_dir = old_dir / "reference"
            for file_name in self.CRITICAL_FILES.keys():
                old_file = old_ref_dir / file_name
                new_file = self.reference_dir / file_name

                if old_file.exists() or new_file.exists():
                    old_content = self.parse_markdown_file(old_file) if old_file.exists() else {}
                    new_content = self.parse_markdown_file(new_file) if new_file.exists() else {}

                    diffs = self.compute_diff(old_content, new_content, file_name)
                    if diffs:
                        all_diffs.extend(diffs)
                        files_changed.append(file_name)

        elif new_files:
            # 对比文件内容
            for file_name, new_content_str in new_files.items():
                if file_name in self.CRITICAL_FILES:
                    old_file = self.reference_dir / file_name
                    old_content = self.parse_markdown_file(old_file) if old_file.exists() else {}

                    # 解析新内容
                    from io import StringIO
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                        f.write(new_content_str)
                        temp_path = Path(f.name)

                    try:
                        new_content = self.parse_markdown_file(temp_path)
                        diffs = self.compute_diff(old_content, new_content, file_name)
                        if diffs:
                            all_diffs.extend(diffs)
                            files_changed.append(file_name)
                    finally:
                        temp_path.unlink()

        # 评估影响
        impact = self.assess_impact(all_diffs)

        # 生成审查结论
        conclusion = self._generate_conclusion(impact, all_diffs)

        return {
            "review_timestamp": datetime.now().isoformat(),
            "files_changed": files_changed,
            "diffs": [asdict(d) for d in all_diffs],
            "impact_assessment": asdict(impact),
            "conclusion": conclusion,
            "approved": impact.risk_level in [ChangeSeverity.LOW, ChangeSeverity.NONE],
            "requires_manual_review": impact.risk_level in [ChangeSeverity.BREAKING, ChangeSeverity.HIGH]
        }

    def _generate_conclusion(self, impact: ImpactAssessment, diffs: List[ChangeDiff]) -> str:
        """生成审查结论文本"""
        if impact.risk_level == ChangeSeverity.NONE:
            return "无实质性变更，无需审查。"
        elif impact.risk_level == ChangeSeverity.LOW:
            return "变更影响较小，可自动通过。"
        elif impact.risk_level == ChangeSeverity.MEDIUM:
            return "变更有一定影响，建议人工确认后执行。"
        elif impact.risk_level == ChangeSeverity.HIGH:
            return "变更影响较大，必须人工审查并制定过渡方案。"
        else:
            return "破坏性变更！需要严格审查并制定完整的迁移方案。"


def format_review_report(review_result: Dict[str, Any]) -> str:
    """格式化审查报告为 Markdown"""
    report = []

    report.append("# 角色设定变更审查报告")
    report.append(f"**审查时间**: {review_result['review_timestamp']}")
    report.append("")

    # 结论摘要
    report.append("## 审查结论")
    conclusion = review_result["conclusion"]
    approved = review_result["approved"]
    requires_review = review_result["requires_manual_review"]

    status_icon = "✅" if approved else "⚠️" if requires_review else "❌"
    report.append(f"{status_icon} **状态**: {conclusion}")

    if requires_review:
        report.append("> ⚠️ **此变更需要人工审查确认**")
    report.append("")

    # 变更文件
    report.append("## 变更文件")
    for file in review_result["files_changed"]:
        report.append(f"- {file}")
    report.append("")

    # 影响评估
    impact = review_result["impact_assessment"]
    report.append("## 影响评估")

    report.append(f"**风险等级**: {impact['risk_level']}")
    report.append("")

    report.append("**影响领域**:")
    for area in impact["affected_areas"]:
        report.append(f"- {area}")
    report.append("")

    if impact["mitigation_suggestions"]:
        report.append("**注意事项**:")
        for suggestion in impact["mitigation_suggestions"]:
            report.append(f"- {suggestion}")
        report.append("")

    if impact["review_checklist"]:
        report.append("**审查清单**:")
        for item in impact["review_checklist"]:
            report.append(f"- [ ] {item}")
        report.append("")

    # 详细变更
    if review_result["diffs"]:
        report.append("## 详细变更")

        # 按文件分组
        diffs_by_file = {}
        for d in review_result["diffs"]:
            file = d["file_path"]
            if file not in diffs_by_file:
                diffs_by_file[file] = []
            diffs_by_file[file].append(d)

        for file, file_diffs in diffs_by_file.items():
            report.append(f"### {file}")

            for d in file_diffs:
                report.append(f"**章节**: {d['section']}")
                report.append(f"**类型**: {d['change_type']}")

                if d["old_value"]:
                    report.append("**旧值**:")
                    report.append("```")
                    report.append(d["old_value"][:200] + ("..." if len(d["old_value"]) > 200 else ""))
                    report.append("```")

                if d["new_value"]:
                    report.append("**新值**:")
                    report.append("```")
                    report.append(d["new_value"][:200] + ("..." if len(d["new_value"]) > 200 else ""))
                    report.append("```")

                report.append("")

    return "\n".join(report)


def main():
    """测试函数"""
    # 示例：审查当前目录与某个旧版本的差异
    profile_dir = Path(__file__).parent.parent

    if profile_dir.exists():
        reviewer = PersonaChangeReviewer(profile_dir)
        # 这里可以传入 old_dir 或 new_files 进行实际对比
        print("审查器已初始化")
        print(f"配置目录: {profile_dir}")


if __name__ == "__main__":
    main()
