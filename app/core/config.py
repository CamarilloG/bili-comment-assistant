import yaml
import os
import copy
from typing import Dict, Any, List

# 默认配置文件：相对本文件所在目录，与面板读写同一 app/config.yaml
_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONFIG_PATH = os.path.join(_CONFIG_DIR, "config.yaml")


class ConfigValidator:
    
    DEFAULT_CONFIG = {
        "account": {
            "cookie_file": "cookies.json",
            "skip_history": True
        },
        "search": {
            "keywords": [],
            "max_videos_per_keyword": 5,
            "filter": {
                "sort": "totalrank",
                "duration": 0
            },
            "strategy": {
                "selection": "order",
                "random_pool_size": 20
            }
        },
        "comment": {
            "texts": [],
            "images": [],
            "enable_image": False
        },
        "behavior": {
            "min_delay": 5,
            "max_delay": 15,
            "headless": False,
            "timeout": 30000
        },
        "browser": {
            "path": "",
            "port": 0
        },
        "captcha": {
            "max_count": 3,
            "quiet_minutes": 5,
            "warmup_minutes": 30,
            "cd_warmup_hours": 3
        },
        "ai": {
            "model_id": "deepseek_chat",
            "timeout": 30,
            "max_retries": 2,
            "comment": {
                "enabled": True,
                "max_comments": 10,
                "max_related": 5,
                "user_intent": "",
                "style": "casual",
                "max_length": 100,
                "min_length": 10,
                "enable_image": False,
                "images": []
            },
            "filter": {
                "enabled": True,
                "criteria": "",
                "sensitivity": 50,
                "use_comments": False,
                "use_related": False,
                "max_comments": 10,
                "max_related": 5
            }
        }
    }
    
    @staticmethod
    def load_config(path: str | None = None) -> Dict[str, Any]:
        """加载配置文件。

        Args:
            path: 配置文件路径。如果为 None，使用 DEFAULT_CONFIG_PATH（不推荐，仅用于向后兼容）。
                  多实例环境下应使用 slot.get_config_path(slot_id) 获取路径。
        """
        if path is None:
            from utils.logger import get_logger
            logger = get_logger()
            logger.warning(f"load_config() called without path, using DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}")
            path = DEFAULT_CONFIG_PATH

        if not os.path.exists(path):
            import copy
            default = copy.deepcopy(ConfigValidator.DEFAULT_CONFIG)
            default["search"]["keywords"] = ["示例关键词"]
            default["comment"]["texts"] = ["默认评论"]
            ConfigValidator.save_config(default, path)
        
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return ConfigValidator.validate_and_fill_defaults(config)
    
    @staticmethod
    def validate_and_fill_defaults(config: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
        # 使用深拷贝避免修改 DEFAULT_CONFIG
        validated = copy.deepcopy(ConfigValidator.DEFAULT_CONFIG)
        
        if not config:
            return validated
        
        if "account" in config:
            validated["account"].update(config["account"])
            if "skip_history" in config["account"]:
                validated["account"]["skip_history"] = bool(config["account"]["skip_history"])
        
        if "search" in config:
            if "keywords" in config["search"]:
                validated["search"]["keywords"] = config["search"]["keywords"]
            if "max_videos_per_keyword" in config["search"]:
                validated["search"]["max_videos_per_keyword"] = max(1, int(config["search"]["max_videos_per_keyword"]))
            
            if "filter" in config["search"]:
                validated["search"]["filter"].update(config["search"]["filter"])
                if validated["search"]["filter"]["sort"] not in ["totalrank", "pubdate", "click", "dm", "stow"]:
                    validated["search"]["filter"]["sort"] = "totalrank"
                if validated["search"]["filter"]["duration"] not in [0, 1, 2, 3, 4]:
                    validated["search"]["filter"]["duration"] = 0
            
            if "strategy" in config["search"]:
                validated["search"]["strategy"].update(config["search"]["strategy"])
                if validated["search"]["strategy"]["selection"] not in ["order", "random"]:
                    validated["search"]["strategy"]["selection"] = "order"
                validated["search"]["strategy"]["random_pool_size"] = max(1, int(validated["search"]["strategy"]["random_pool_size"]))
        
        if "comment" in config:
            if "texts" in config["comment"]:
                validated["comment"]["texts"] = config["comment"]["texts"]
            if "images" in config["comment"]:
                raw = config["comment"]["images"]
                validated["comment"]["images"] = [raw] if isinstance(raw, str) and raw.strip() else (raw if isinstance(raw, list) else [])
            if "enable_image" in config["comment"]:
                validated["comment"]["enable_image"] = bool(config["comment"]["enable_image"])
        
        if "behavior" in config:
            if "min_delay" in config["behavior"]:
                validated["behavior"]["min_delay"] = max(0, float(config["behavior"]["min_delay"]))
            if "max_delay" in config["behavior"]:
                validated["behavior"]["max_delay"] = max(validated["behavior"]["min_delay"], float(config["behavior"]["max_delay"]))
            if "headless" in config["behavior"]:
                validated["behavior"]["headless"] = bool(config["behavior"]["headless"])
            if "timeout" in config["behavior"]:
                validated["behavior"]["timeout"] = max(1000, int(config["behavior"]["timeout"]))
        
        if "browser" in config:
            validated["browser"] = config["browser"]
        
        if "captcha" in config:
            captcha = config["captcha"]
            if "max_count" in captcha:
                validated["captcha"]["max_count"] = max(1, int(captcha["max_count"]))
            if "quiet_minutes" in captcha:
                validated["captcha"]["quiet_minutes"] = max(1, int(captcha["quiet_minutes"]))
            if "warmup_minutes" in captcha:
                validated["captcha"]["warmup_minutes"] = max(5, int(captcha["warmup_minutes"]))
            if "cd_warmup_hours" in captcha:
                validated["captcha"]["cd_warmup_hours"] = max(1, int(captcha["cd_warmup_hours"]))
        
        if "ai" in config:
            ai = config["ai"]
            ai_default = ConfigValidator.DEFAULT_CONFIG["ai"]
            raw_id = ai.get("model_id") or (str(ai.get("model", "")).replace("-", "_") if ai.get("model") else None)
            model_id = str(raw_id or ai_default["model_id"])
            validated["ai"] = {
                "model_id": model_id,
                "timeout": max(5, int(ai.get("timeout", ai_default["timeout"]))),
                "max_retries": max(0, int(ai.get("max_retries", ai_default["max_retries"]))),
                "comment": {
                    "enabled": bool(ai.get("comment", {}).get("enabled", ai_default["comment"]["enabled"])),
                    "max_comments": max(1, min(30, int(ai.get("comment", {}).get("max_comments") or ai.get("filter", {}).get("max_comments", ai_default["comment"]["max_comments"])))),
                    "max_related": max(1, min(20, int(ai.get("comment", {}).get("max_related") or ai.get("filter", {}).get("max_related", ai_default["comment"]["max_related"])))),
                    "user_intent": str(ai.get("comment", {}).get("user_intent", ai_default["comment"]["user_intent"])),
                    "style": str(ai.get("comment", {}).get("style", ai_default["comment"]["style"])),
                    "max_length": max(10, int(ai.get("comment", {}).get("max_length", ai_default["comment"]["max_length"]))),
                    "min_length": max(1, int(ai.get("comment", {}).get("min_length", ai_default["comment"]["min_length"]))),
                    "enable_image": bool(ai.get("comment", {}).get("enable_image", ai_default["comment"]["enable_image"])),
                    "images": list(ai.get("comment", {}).get("images", ai_default["comment"]["images"]) or []),
                },
                "filter": {
                    "enabled": bool(ai.get("filter", {}).get("enabled", ai_default["filter"]["enabled"])),
                    "criteria": str(ai.get("filter", {}).get("criteria", ai_default["filter"]["criteria"])),
                    "sensitivity": max(1, min(100, int(ai.get("filter", {}).get("sensitivity", ai_default["filter"]["sensitivity"])))),
                    "use_comments": bool(ai.get("filter", {}).get("use_comments", ai_default["filter"]["use_comments"])),
                    "use_related": bool(ai.get("filter", {}).get("use_related", ai_default["filter"]["use_related"])),
                    "max_comments": max(1, min(30, int(ai.get("filter", {}).get("max_comments", ai_default["filter"]["max_comments"])))),
                    "max_related": max(1, min(20, int(ai.get("filter", {}).get("max_related", ai_default["filter"]["max_related"])))),
                },
            }

        if "warmup" in config:
            validated["warmup"] = config["warmup"]

        # 保留 bots 配置（机器人通知）
        if "bots" in config:
            validated["bots"] = config["bots"]

        if strict:
            ConfigValidator._validate_required_fields(validated)

        return validated
    
    @staticmethod
    def _validate_required_fields(config: Dict[str, Any]) -> None:
        if not config["search"]["keywords"]:
            raise ValueError("At least one search keyword is required!")
        
        if not config["comment"]["texts"]:
            raise ValueError("At least one comment text is required!")
        
        # 智能评论/智能筛选开关仅影响「AI 评论模式」；未配置 api_key 时运行时不会启用 AI，不在此处强制要求，避免普通模板评论也报错
        # （AIManager 在无 api_key 时不创建 provider，is_comment_enabled/is_filter_enabled 为 False，会走模板评论）
    
    @staticmethod
    def save_config(config: Dict[str, Any], path: str | None = None) -> None:
        """保存配置到文件。

        Args:
            config: 配置字典
            path: 配置文件路径。如果为 None，使用 DEFAULT_CONFIG_PATH（不推荐，仅用于向后兼容）。
                  多实例环境下应使用 slot.get_config_path(slot_id) 获取路径。
        """
        if path is None:
            from utils.logger import get_logger
            logger = get_logger()
            logger.warning(f"save_config() called without path, using DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}")
            path = DEFAULT_CONFIG_PATH

        path = os.path.abspath(path)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
