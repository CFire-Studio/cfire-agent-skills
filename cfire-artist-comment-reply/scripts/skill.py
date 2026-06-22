"""CFIRE 艺人评论回复技能

通过艺人独立 API Key 鉴权调用服务端接口，获取未读评论并引导智能体生成符合人设的回复。
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 导入公共配置加载器
sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))
from config_loader import load_config, get_artist_config, get_api_base_url


class CfireArtistCommentReplySkill:
    """CFIRE 艺人评论回复技能类"""

    def __init__(self):
        self.config = load_config()
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """初始化日志：写入 scripts/logs/skill.log，编码 UTF-8。"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        logger = logging.getLogger("cfire_artist_comment_reply")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            fh = logging.FileHandler(log_dir / "skill.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        return logger

    def _get_api_url(self, path: str) -> str:
        base = get_api_base_url()
        return f"{base}{path}"

    def _resolve_artist_id(self, id_or_name: str) -> str:
        """将艺人名称或 artist_id 解析为艺人名称（配置 key），支持大小写不敏感匹配。"""
        needle_raw = str(id_or_name).strip()
        if not needle_raw:
            raise ValueError("artist_id 不能为空")
        artists = self.config.get("artists", {})

        if needle_raw in artists:
            return needle_raw

        needle = needle_raw.lower()
        for name in artists:
            if name.lower() == needle:
                return name

        for name, cfg in artists.items():
            if isinstance(cfg, dict) and cfg.get("artist_id") == needle_raw:
                return name

        raise ValueError(
            f"未找到艺人 '{id_or_name}'。已配置艺人：{self._format_artist_list()}"
        )

    def _get_artist_config(self, artist_name: str) -> Optional[Dict[str, Any]]:
        artists = self.config.get("artists")
        if not isinstance(artists, dict):
            return None
        cfg = artists.get(artist_name)
        if isinstance(cfg, dict):
            return cfg
        if isinstance(cfg, str):
            return {"api_key": cfg}
        return None

    def _get_artist_api_key(self, artist_name: str) -> str:
        cfg = self._get_artist_config(artist_name)
        if cfg is None:
            return ""
        return cfg.get("api_key", "")

    def _format_artist_list(self) -> str:
        artists = self.config.get("artists", {})
        if not isinstance(artists, dict) or not artists:
            return "无"
        lines = []
        for name, cfg in artists.items():
            artist_id = cfg.get("artist_id", "") if isinstance(cfg, dict) else ""
            lines.append(f"  - {name} ({artist_id})" if artist_id else f"  - {name}")
        return "\n" + "\n".join(lines)

    def _get_artist_api_id(self, artist_name: str) -> str:
        cfg = self._get_artist_config(artist_name)
        if cfg is None:
            return artist_name
        return cfg.get("artist_id") or artist_name

    def list_unread_comments(
        self,
        artist_id: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取艺人的未读评论列表。"""
        resolved_name = self._resolve_artist_id(artist_id)
        api_key = self._get_artist_api_key(resolved_name)
        if not api_key:
            msg = f"艺人 '{artist_id}' (name={resolved_name}) 未配置 API Key。"
            self.logger.error(msg)
            raise ValueError(msg)

        api_artist_id = self._get_artist_api_id(resolved_name)

        url = self._get_api_url("/api/artist/comments/unread")
        headers = {"X-Artist-API-Key": api_key}
        params = {}
        if limit:
            params["limit"] = min(limit, 10)

        self.logger.info(f"获取未读评论: artist={api_artist_id}, limit={limit}")
        resp = requests.get(url, headers=headers, params=params, timeout=30)

        try:
            result = resp.json()
        except json.JSONDecodeError:
            result = {"raw": resp.text}

        if resp.status_code == 200:
            self.logger.info(f"获取未读评论成功: artist={api_artist_id}, total={result.get('total', 0)}")
            return result
        elif resp.status_code == 400:
            msg = f"请求参数错误: {result.get('error', '未知')}"
            self.logger.error(f"获取未读评论失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 401:
            msg = f"鉴权失败: {result.get('error', '未知')}（请确认 API Key 与 artist_id 匹配且未过期）"
            self.logger.error(f"获取未读评论失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        else:
            error = result.get("error", f"HTTP {resp.status_code}")
            self.logger.error(f"获取未读评论失败: artist={api_artist_id}, error={error}")
            raise RuntimeError(f"获取未读评论失败: {error}")

    def reply_to_comment(
        self,
        artist_id: str,
        comment_id: str,
        reply_content: str,
    ) -> Dict[str, Any]:
        """回复指定的评论。"""
        resolved_name = self._resolve_artist_id(artist_id)
        api_key = self._get_artist_api_key(resolved_name)
        if not api_key:
            msg = f"艺人 '{artist_id}' (name={resolved_name}) 未配置 API Key。"
            self.logger.error(msg)
            raise ValueError(msg)

        api_artist_id = self._get_artist_api_id(resolved_name)
        reply_content = str(reply_content).strip()
        if not reply_content:
            raise ValueError("回复内容不能为空")
        if not comment_id:
            raise ValueError("评论 ID 不能为空")

        url = self._get_api_url(f"/api/artist/comments/{comment_id}/reply")
        headers = {"X-Artist-API-Key": api_key}
        data = {"artist_id": api_artist_id, "content": reply_content}

        self.logger.info(f"回复评论: artist={api_artist_id}, comment={comment_id}")
        resp = requests.post(url, headers=headers, json=data, timeout=30)

        try:
            result = resp.json()
        except json.JSONDecodeError:
            result = {"raw": resp.text}

        if resp.status_code == 201:
            self.logger.info(f"回复成功: artist={api_artist_id}, comment={comment_id}")
            return result
        elif resp.status_code == 400:
            msg = f"请求参数错误: {result.get('error', '未知')}"
            self.logger.error(f"回复失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 401:
            msg = f"鉴权失败: {result.get('error', '未知')}"
            self.logger.error(f"回复失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 403:
            msg = f"评论不属于该艺人: {result.get('error', '未知')}"
            self.logger.error(f"回复失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 404:
            msg = f"评论不存在: {result.get('error', '未知')}"
            self.logger.error(f"回复失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        else:
            error = result.get("error", f"HTTP {resp.status_code}")
            self.logger.error(f"回复失败: artist={api_artist_id}, error={error}")
            raise RuntimeError(f"回复失败: {error}")


def _main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="CFIRE 艺人评论回复 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    list_cmd = sub.add_parser("list", help="获取未读评论列表")
    list_cmd.add_argument("--artist", "-a", required=True, help="艺人名称或 artist_id")
    list_cmd.add_argument("--limit", "-n", type=int, help="获取数量（最大 10）")

    reply_cmd = sub.add_parser("reply", help="回复指定评论")
    reply_cmd.add_argument("--artist", "-a", required=True, help="艺人名称或 artist_id")
    reply_cmd.add_argument("--comment", "-c", required=True, help="评论 ID")
    reply_cmd.add_argument("--reply", "-r", required=True, help="回复内容")

    args = parser.parse_args()
    skill = CfireArtistCommentReplySkill()

    try:
        if args.cmd == "list":
            result = skill.list_unread_comments(artist_id=args.artist, limit=args.limit)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.cmd == "reply":
            result = skill.reply_to_comment(
                artist_id=args.artist,
                comment_id=args.comment,
                reply_content=args.reply,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
