"""CFIRE 艺人动态发布技能

通过艺人独立 API Key 鉴权调用服务端接口，为艺人发布文字或图文动态。
"""

import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 导入公共配置加载器
sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))
from config_loader import load_config, get_artist_config, get_api_base_url, save_config


class CfireArtistPostSkill:
    """CFIRE 艺人动态发布技能类"""

    ENERGY_COST_TEXT_POST = 10
    ENERGY_COST_IMAGE_POST = 50

    ENERGY_COST_GROWTH_TEXT = 10
    ENERGY_COST_GROWTH_IMAGE = 50
    ENERGY_COST_GROWTH_VIDEO = 50

    def __init__(
        self,
        config_path: Optional[Path] = None,
        auto_refresh: bool = True,
    ):
        # 使用公共配置加载器
        self.config = load_config()
        self.logger = self._setup_logging()

    def _discover_config_path(self) -> Path:
        """自动发现配置文件：从脚本目录向上逐级查找 config.json。"""
        start = Path(__file__).parent.resolve()
        for path in [start, *start.parents]:
            candidate = path / "config.json"
            if candidate.exists():
                return candidate
        return start / "config.json"

    def _apply_env_overrides(self) -> None:
        """用环境变量覆盖配置，提高容器化/CI 场景的自动化水平。"""
        env_url = os.getenv("CFIRE_API_BASE_URL")
        if env_url:
            self.config["api_base_url"] = env_url
            self.logger.debug(f"环境变量覆盖 API Base URL: {env_url}")

    def _setup_logging(self) -> logging.Logger:
        """初始化日志：写入 scripts/logs/skill.log，编码 UTF-8。"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        logger = logging.getLogger("cfire_artist_post")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            fh = logging.FileHandler(log_dir / "skill.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        return logger

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        return {"api_base_url": "http://localhost:19901", "artists": {}}

    def _save_config(self) -> None:
        save_config(self.config)

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
        """安全读取单个艺人配置，返回标准化的 dict 或 None。"""
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
        """根据艺人名称（配置 key）获取用于 API 请求的 artist_id。"""
        cfg = self._get_artist_config(artist_name)
        if cfg is None:
            return artist_name
        return cfg.get("artist_id") or artist_name

    def _get_default_user_id(self, artist_name: str) -> Optional[str]:
        """从配置中获取默认的 user_id。"""
        cfg = self._get_artist_config(artist_name)
        if cfg is None:
            return None
        uid = cfg.get("user_id")
        return str(uid).strip() if uid else None

    def publish_post(
        self,
        artist_id: str,
        content: str,
        user_id: Optional[str] = None,
        images: Optional[List[str]] = None,
        video_url: Optional[str] = None,
        post_type: str = "standard",
        initial_form: str = "text",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_name = self._resolve_artist_id(artist_id)

        if user_id is None:
            user_id = self._get_default_user_id(resolved_name)
        user_id = str(user_id).strip() if user_id else ""
        content = str(content).strip()
        post_type = str(post_type).strip().lower()
        initial_form = str(initial_form).strip().lower()

        if not user_id:
            raise ValueError("user_id 不能为空（请传入参数或在配置中设置默认 user_id）")
        if not content:
            raise ValueError("content 不能为空")
        if images and len(images) > 9:
            raise ValueError("图片数量不能超过 9 张")
        if post_type not in ("standard", "diary", "growth"):
            raise ValueError("post_type 必须是 standard、diary 或 growth")
        if post_type == "growth" and initial_form not in ("text", "image", "video"):
            raise ValueError("initial_form 必须是 text、image 或 video")

        api_key = self._get_artist_api_key(resolved_name)
        if not api_key:
            msg = (
                f"艺人 '{artist_id}' (name={resolved_name}) 未配置 API Key。"
                f"请在 config.json 中配置 api_key。"
            )
            self.logger.error(msg)
            raise ValueError(msg)

        api_artist_id = self._get_artist_api_id(resolved_name)

        video_url = str(video_url).strip() if video_url else None
        has_images = images and len(images) > 0
        has_video = bool(video_url)
        has_media = has_images or has_video

        if post_type == "growth":
            if initial_form == "text":
                cost = self.ENERGY_COST_GROWTH_TEXT
            elif initial_form == "image":
                cost = self.ENERGY_COST_GROWTH_IMAGE
                if not has_images:
                    raise ValueError("growth 初始形态为 image 时必须提供图片")
            elif initial_form == "video":
                cost = self.ENERGY_COST_GROWTH_VIDEO
                if not has_video:
                    raise ValueError("growth 初始形态为 video 时必须提供 video_url")
        else:
            cost = self.ENERGY_COST_IMAGE_POST if has_media else self.ENERGY_COST_TEXT_POST

        url = self._get_api_url("/api/artist/posts")
        headers = {"X-Artist-API-Key": api_key}

        data = {
            "artist_id": api_artist_id,
            "user_id": user_id,
            "content": content,
        }
        if post_type != "standard":
            data["post_type"] = post_type
        if post_type == "growth":
            data["initial_form"] = initial_form
        if video_url:
            data["video_url"] = video_url
        if idempotency_key:
            data["idempotency_key"] = idempotency_key
        else:
            data["idempotency_key"] = str(uuid.uuid4())

        files = []
        opened_files = []
        try:
            if images:
                for img_path in images:
                    f = open(img_path, "rb")
                    opened_files.append(f)
                    filename = Path(img_path).name
                    files.append(("images", (filename, f)))

            self.logger.info(
                f"发布动态: artist={api_artist_id}, user={user_id}, "
                f"images={len(images) if images else 0}, video={bool(video_url)}, cost={cost}"
            )
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=30)
        finally:
            for f in opened_files:
                f.close()

        try:
            result = resp.json()
        except json.JSONDecodeError:
            result = {"raw": resp.text}

        if resp.status_code == 201:
            self.logger.info(f"发布成功: artist={api_artist_id}, response={result}")
            return result
        elif resp.status_code == 400:
            msg = f"请求参数错误: {result.get('error', '未知')}（请检查 artist_id / content / user_id 是否为空）"
            self.logger.error(f"发布失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 401:
            msg = f"鉴权失败: {result.get('error', '未知')}（请确认 API Key 与 artist_id 匹配且未过期，不要修改代码）"
            self.logger.error(f"发布失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 403:
            msg = f"能量不足: {result.get('error', '未知')}（无需重试，请先补充能量）"
            self.logger.error(f"发布失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 404:
            msg = f"用户不存在: {result.get('error', '未知')}（请检查 user_id 是否正确）"
            self.logger.error(f"发布失败: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 409:
            msg = f"重复请求: {result.get('error', '未知')}（幂等键冲突，可视为已处理，无需重试）"
            self.logger.warning(f"发布警告: artist={api_artist_id}, {msg}")
            raise RuntimeError(msg)
        else:
            error = result.get("error", f"HTTP {resp.status_code}")
            self.logger.error(f"发布失败: artist={api_artist_id}, error={error}")
            raise RuntimeError(f"发布失败: {error}")

    def update_growth_form(
        self,
        artist_id: str,
        post_id: str,
        form: str,
        content: Optional[str] = None,
        images: Optional[List[str]] = None,
        video_url: Optional[str] = None,
        set_as_current: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """为可持续生长动态追加或更新指定形态。

        Args:
            artist_id: 艺人名称或 artist_id
            post_id: 动态 ID
            form: 形态，必须是 text、image 或 video
            content: 文字内容（可选）
            images: 图片路径列表，form='image' 时必需
            video_url: 外部视频链接，form='video' 时必需
            set_as_current: 是否将该形态设为当前默认展示形态
            idempotency_key: 幂等键（可选）
        """
        resolved_name = self._resolve_artist_id(artist_id)
        form = str(form).strip().lower()
        if form not in ("text", "image", "video"):
            raise ValueError("form 必须是 text、image 或 video")

        user_id = self._get_default_user_id(resolved_name)
        user_id = str(user_id).strip() if user_id else ""
        if not user_id:
            raise ValueError("user_id 不能为空（请在配置中设置默认 user_id）")

        if form == "image" and (not images or len(images) == 0):
            raise ValueError("form='image' 时必须提供图片")
        if form == "video" and not video_url:
            raise ValueError("form='video' 时必须提供 video_url")
        if images and len(images) > 9:
            raise ValueError("图片数量不能超过 9 张")

        api_key = self._get_artist_api_key(resolved_name)
        if not api_key:
            msg = (
                f"艺人 '{artist_id}' (name={resolved_name}) 未配置 API Key。"
                f"请在 config.json 中配置 api_key。"
            )
            self.logger.error(msg)
            raise ValueError(msg)

        api_artist_id = self._get_artist_api_id(resolved_name)

        url = self._get_api_url(f"/api/artist/posts/{post_id}/forms/{form}")
        headers = {"X-Artist-API-Key": api_key}

        data: Dict[str, Any] = {
            "user_id": user_id
        }
        if content is not None:
            data["content"] = str(content).strip()
        if video_url:
            data["video_url"] = str(video_url).strip()
        if set_as_current:
            data["set_as_current"] = "true"
        if idempotency_key:
            data["idempotency_key"] = idempotency_key
        else:
            data["idempotency_key"] = str(uuid.uuid4())

        files = []
        opened_files = []
        try:
            if images:
                for img_path in images:
                    f = open(img_path, "rb")
                    opened_files.append(f)
                    filename = Path(img_path).name
                    files.append(("images", (filename, f)))

            self.logger.info(
                f"更新 growth 形态: post={post_id}, form={form}, "
                f"artist={api_artist_id}, images={len(images) if images else 0}, "
                f"video={bool(video_url)}, set_as_current={set_as_current}"
            )
            resp = requests.put(url, headers=headers, data=data, files=files, timeout=30)
        finally:
            for f in opened_files:
                f.close()

        try:
            result = resp.json()
        except json.JSONDecodeError:
            result = {"raw": resp.text}

        if resp.status_code == 200:
            self.logger.info(f"更新形态成功: post={post_id}, form={form}, response={result}")
            return result
        elif resp.status_code == 400:
            msg = f"请求参数错误: {result.get('error', '未知')}（请检查 post_id、form、content 等参数）"
            self.logger.error(f"更新形态失败: post={post_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 401:
            msg = f"鉴权失败: {result.get('error', '未知')}（请确认 API Key 与 artist_id 匹配且未过期，不要修改代码）"
            self.logger.error(f"更新形态失败: post={post_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 403:
            msg = f"能量不足: {result.get('error', '未知')}（无需重试，请先补充能量）"
            self.logger.error(f"更新形态失败: post={post_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 404:
            msg = f"动态不存在或无权访问: {result.get('error', '未知')}（请检查 post_id 是否正确）"
            self.logger.error(f"更新形态失败: post={post_id}, {msg}")
            raise RuntimeError(msg)
        elif resp.status_code == 409:
            msg = f"重复请求: {result.get('error', '未知')}（幂等键冲突，可视为已处理，无需重试）"
            self.logger.warning(f"更新形态警告: post={post_id}, {msg}")
            raise RuntimeError(msg)
        else:
            error = result.get("error", f"HTTP {resp.status_code}")
            self.logger.error(f"更新形态失败: post={post_id}, error={error}")
            raise RuntimeError(f"更新形态失败: {error}")


def _main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="CFIRE 艺人动态发布 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pub = sub.add_parser("publish", help="发布动态")
    pub.add_argument("--artist", "-a", required=True, help="艺人名称或 artist_id")
    pub.add_argument("--content", "-c", required=True, help="动态文本内容")
    pub.add_argument("--user", "-u", help="操作用户 ID（未提供时读取配置默认 user_id）")
    pub.add_argument("--images", "-i", nargs="*", help="图片路径（最多 9 张）")
    pub.add_argument("--video", "-v", help="外部视频链接（Bilibili、YouTube、TikTok、抖音、快手）")
    pub.add_argument("--post-type", "-t", default="standard", help="动态类型：standard（默认）、diary、growth")
    pub.add_argument("--initial-form", "-f", default="text", help="growth 动态初始形态：text（默认）、image、video")

    upd = sub.add_parser("update-form", help="更新或追加 growth 动态形态")
    upd.add_argument("--artist", "-a", required=True, help="艺人名称或 artist_id")
    upd.add_argument("--post-id", "-p", required=True, help="动态 ID")
    upd.add_argument("--form", "-F", required=True, choices=["text", "image", "video"], help="要更新或追加的形态")
    upd.add_argument("--content", "-c", help="文字内容")
    upd.add_argument("--images", "-i", nargs="*", help="图片路径（form=image 时必需，最多 9 张）")
    upd.add_argument("--video", "-v", help="外部视频链接（form=video 时必需）")
    upd.add_argument("--set-current", "-s", action="store_true", help="设为当前默认展示形态")

    args = parser.parse_args()
    skill = CfireArtistPostSkill()

    try:
        if args.cmd == "publish":
            result = skill.publish_post(
                artist_id=args.artist,
                content=args.content,
                user_id=args.user,
                images=args.images,
                video_url=args.video,
                post_type=args.post_type,
                initial_form=args.initial_form,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.cmd == "update-form":
            result = skill.update_growth_form(
                artist_id=args.artist,
                post_id=args.post_id,
                form=args.form,
                content=args.content,
                images=args.images,
                video_url=args.video,
                set_as_current=args.set_current,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
