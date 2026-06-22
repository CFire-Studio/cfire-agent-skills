"""
统一配置加载器
所有 Agent Skill 共享使用这个模块加载配置，避免重复维护多个 config.json 文件
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# 全局配置缓存
_global_config: Optional[Dict[str, Any]] = None
_global_config_path: Optional[Path] = None


def get_config_path() -> Path:
    """获取全局配置文件路径，优先使用项目根目录的 config.json"""
    global _global_config_path
    if _global_config_path is not None:
        return _global_config_path
    
    # 从当前文件所在目录（项目根目录）查找 config.json
    root_dir = Path(__file__).parent.resolve()
    config_path = root_dir / "config.json"
    
    if config_path.exists():
        _global_config_path = config_path
        return config_path
    
    # 兼容旧版本：如果根目录没有，向上查找
    start = Path.cwd()
    for path in [start, *start.parents]:
        candidate = path / "config.json"
        if candidate.exists():
            _global_config_path = candidate
            return candidate
    
    # 如果都没有，返回根目录默认路径
    _global_config_path = root_dir / "config.json"
    return _global_config_path


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    加载全局配置
    :param force_reload: 是否强制重新加载配置，即使已经缓存
    """
    global _global_config
    if _global_config is not None and not force_reload:
        return _global_config.copy()
    
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            _global_config = json.load(f)
    else:
        # 默认配置
        _global_config = {
            "api_base_url": "http://localhost:19901",
            "artists": {}
        }
    
    # 应用环境变量覆盖
    _apply_env_overrides(_global_config)
    
    return _global_config.copy()


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到全局配置文件"""
    global _global_config
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    _global_config = config.copy()


def _apply_env_overrides(config: Dict[str, Any]) -> None:
    """用环境变量覆盖配置，提高容器化/CI场景的自动化水平"""
    env_url = os.getenv("CFIRE_API_BASE_URL")
    if env_url:
        config["api_base_url"] = env_url
    
    # 支持通过环境变量配置艺人API Key（格式：CFIRE_ARTIST_{NAME}_API_KEY）
    for key, value in os.environ.items():
        if key.startswith("CFIRE_ARTIST_") and key.endswith("_API_KEY"):
            artist_name = key[12:-8].replace("_", " ")
            if "artists" not in config:
                config["artists"] = {}
            if artist_name not in config["artists"]:
                config["artists"][artist_name] = {}
            config["artists"][artist_name]["api_key"] = value


def get_artist_config(artist_id_or_name: str) -> Optional[Dict[str, Any]]:
    """
    根据艺人名称或ID获取配置
    :param artist_id_or_name: 艺人名称、artist_id或user_id
    """
    config = load_config()
    artists = config.get("artists", {})
    
    # 直接匹配名称
    if artist_id_or_name in artists:
        return artists[artist_id_or_name].copy()
    
    # 不区分大小写匹配名称
    needle = artist_id_or_name.lower()
    for name, cfg in artists.items():
        if name.lower() == needle:
            return cfg.copy()
    
    # 匹配artist_id
    for name, cfg in artists.items():
        if isinstance(cfg, dict) and cfg.get("artist_id") == artist_id_or_name:
            return cfg.copy()
    
    # 匹配user_id
    for name, cfg in artists.items():
        if isinstance(cfg, dict) and cfg.get("user_id") == artist_id_or_name:
            return cfg.copy()
    
    return None


def get_api_base_url() -> str:
    """获取API基础URL"""
    config = load_config()
    return config.get("api_base_url", "http://localhost:19901").rstrip("/")
